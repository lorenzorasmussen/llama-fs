import asyncio
import json
import os

from groq import Groq
from watchdog.events import FileSystemEvent, FileSystemEventHandler

from src.config import GROQ_API_KEY, LLM_MODEL
from src.loader import get_dir_summaries, get_file_summary
from src.prompts import FILE_PROMPT, WATCH_PROMPT


class Handler(FileSystemEventHandler):
    def __init__(self, base_path, callback, queue):
        self.base_path = base_path
        self.callback = callback
        self.queue = queue
        self.events = []
        self.loop = asyncio.get_running_loop()
        print(f"Watching directory {base_path}")

    async def set_summaries(self):
        print(f"Getting summaries for {self.base_path}")
        self.summaries = await get_dir_summaries(self.base_path)
        self.summaries_cache = {s["file_path"]: s for s in self.summaries}

    def update_summary(self, file_path):
        print(f"Updating summary for {file_path}")
        path = os.path.join(self.base_path, file_path)

        if not os.path.exists(path):
            if file_path in self.summaries_cache:
                self.summaries_cache.pop(file_path)
            return

        future = asyncio.run_coroutine_threadsafe(get_file_summary(path), self.loop)
        summary = future.result()

        if summary:
            self.summaries_cache[file_path] = summary
            self.summaries = list(self.summaries_cache.values())
            self.queue.put(
                {
                    "files": [
                        {
                            "src_path": file_path,
                            "dst_path": file_path,
                            "summary": self.summaries_cache[file_path]["summary"],
                        }
                    ]
                }
            )
        elif file_path in self.summaries_cache:
            self.summaries_cache.pop(file_path)

    def on_created(self, event: FileSystemEvent) -> None:
        src_path = os.path.relpath(event.src_path, self.base_path)
        print(f"Created {src_path}")
        if not event.is_directory:
            self.update_summary(src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        src_path = os.path.relpath(event.src_path, self.base_path)
        print(f"Deleted {src_path}")
        if not event.is_directory:
            self.update_summary(src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        src_path = os.path.relpath(event.src_path, self.base_path)
        print(f"Modified {src_path}")
        if not event.is_directory:
            self.update_summary(src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        src_path = os.path.relpath(event.src_path, self.base_path)
        dest_path = os.path.relpath(event.dest_path, self.base_path)
        print(f"Moved {src_path} > {dest_path}")
        self.events.append({"src_path": src_path, "dst_path": dest_path})
        self.update_summary(src_path)
        self.update_summary(dest_path)
        print("Summaries: ", self.summaries)
        print("Events: ", self.events)
        files = self.callback(
            summaries=self.summaries, fs_events=json.dumps({"files": self.events})
        )

        self.queue.put(files)


def create_file_tree(summaries, fs_events):
    client = Groq(api_key=GROQ_API_KEY)
    watch_prompt_formatted = WATCH_PROMPT.format(fs_events=fs_events)
    cmpl = client.chat.completions.create(
        messages=[
            {"content": FILE_PROMPT, "role": "system"},
            {"content": json.dumps(summaries), "role": "user"},
            {"content": watch_prompt_formatted, "role": "system"},
            {"content": json.dumps(fs_events), "role": "user"},
        ],
        model=LLM_MODEL,
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(cmpl.choices[0].message.content)["files"]
