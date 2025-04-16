import os
import json
import base64
import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep

BOT_TOKEN = os.getenv("7946520115:AAEA_Zq0XI1lyZqWhxTLxjmpryDyKokp4sU")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
session = requests.Session()
user_states = {}

def send_message(chat_id, text):
    session.post(f"{BASE_URL}/sendMessage", data={"chat_id": chat_id, "text": text})

def send_document(chat_id, file_path, caption=""):
    with open(file_path, "rb") as f:
        session.post(
            f"{BASE_URL}/sendDocument",
            data={"chat_id": chat_id, "caption": caption},
            files={"document": f}
        )

def get_updates(offset=None):
    params = {"timeout": 100}
    if offset:
        params["offset"] = offset
    res = session.get(f"{BASE_URL}/getUpdates", params=params)
    return res.json().get("result", [])

# === Your original helper functions should be inserted here ===

def process_command(chat_id, text):
    if text.startswith("/start"):
        send_message(chat_id, "Welcome! Use /setorg <org_code> to begin.")
    elif text.startswith("/setorg"):
        parts = text.split()
        if len(parts) != 2:
            send_message(chat_id, "Usage: /setorg <org_code>")
            return
        org_code = parts[1]
        org_id, org_name = get_org_details(org_code)
        if org_id:
            user_states[chat_id] = {"org_id": org_id, "org_name": org_name}
            send_message(chat_id, f"Org set: {org_name} (ID: {org_id})")
        else:
            send_message(chat_id, "Invalid org code.")
    elif text.startswith("/listcourses"):
        state = user_states.get(chat_id)
        if not state:
            send_message(chat_id, "Set an org first using /setorg")
            return
        updated_base = update_base_url(state["org_id"])
        courses = fetch_json(updated_base)
        if not courses:
            send_message(chat_id, "No courses found.")
            return
        triplets = []
        displayed = set()
        sections = ['popular', 'recent', 'feature', 'all', 'upcomingLiveClasses']
        for sec in sections:
            for course in courses.get("data", {}).get(sec, {}).get("coursesData", []):
                cid = course.get("id")
                name = course.get("name")
                if cid and name and cid not in displayed:
                    triplets.append((cid, name))
                    displayed.add(cid)
        user_states[chat_id]["triplets"] = triplets
        msg = "\n".join([f"{i+1}. {name} (ID: {cid})" for i, (cid, name) in enumerate(triplets)])
        send_message(chat_id, "Available courses:\n" + msg if msg else "No courses found.")
    elif text.startswith("/download"):
        state = user_states.get(chat_id)
        if not state or "triplets" not in state:
            send_message(chat_id, "Use /listcourses first.")
            return
        parts = text.split()
        if len(parts) != 2 or not parts[1].isdigit():
            send_message(chat_id, "Usage: /download <course_number>")
            return
        idx = int(parts[1]) - 1
        if idx < 0 or idx >= len(state["triplets"]):
            send_message(chat_id, "Invalid course number.")
            return
        course_id, course_name = state["triplets"][idx]
        base_url = "https://api.classplusapp.com/v2/course/preview/content/list/eyJjb3Vyc2VJZCI6IjUzNDY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo3NjMzMjAsImNhdGVnb3J5SWQiOm51bGx9?folderId=0&limit=10000&offset=0"
        file_name = re.sub(r'[<>:"/\\|?*]', "_", course_name) + ".txt"
        tmp_path = f"/tmp/{file_name}"
        process_triplet(base_url, state["org_id"], course_id, file_name.replace(".txt", ""), state["org_name"], tmp_path)
        send_document(chat_id, tmp_path, caption=f"Course: {course_name}\nCoaching: {state['org_name']}")
        os.remove(tmp_path)
    else:
        send_message(chat_id, "Unknown command.")

def main():
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message")
            if not msg:
                continue
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")
            if text:
                process_command(chat_id, text)
        sleep(1)

if __name__ == "__main__":
    main()
org_name": org_name}
            send_message(chat_id, f"Org code set: {org_name} (ID: {org_id})")
        else:
            send_message(chat_id, "Invalid org code. Try again.")
    elif text.startswith("/listcourses"):
        if chat_id not in user_states or "org_id" not in user_states[chat_id]:
            send_message(chat_id, "Please set your org first with /setorg <org_code>.")
            return
        org_id = user_states[chat_id]["org_id"]
        updated_base = update_base_url(org_id)
        if updated_base:
            courses = fetch_json(updated_base)
            if courses:
                course_list = "
".join([f"{i+1}. {course.get('name')} : {course.get('id')}" 
                                        for i, course in enumerate(courses.get('data', {}).get('popular', {}).get('coursesData', []))])
                send_message(chat_id, f"Available Courses:
{course_list}")
            else:
                send_message(chat_id, "Failed to fetch courses.")
        else:
            send_message(chat_id, "Failed to update base URL.")
    elif text.startswith("/download"):
        if chat_id not in user_states or "org_id" not in user_states[chat_id]:
            send_message(chat_id, "Please set your org first with /setorg <org_code>.")
            return
        parts = text.split()
        if len(parts) != 2 or not parts[1].isdigit():
            send_message(chat_id, "Usage: /download <course_number>")
            return
        course_number = int(parts[1]) - 1  # List is 0-indexed
        org_id = user_states[chat_id]["org_id"]
        updated_base = update_base_url(org_id)
        if updated_base:
            courses = fetch_json(updated_base)
            if courses:
                course_list = courses.get('data', {}).get('popular', {}).get('coursesData', [])
                if 0 <= course_number < len(course_list):
                    course = course_list[course_number]
                    file_name = f"{course.get('name').replace(' ', '_')}.txt"
                    process_triplet(updated_base, org_id, course.get('id'), file_name, course.get('name'))
                    send_message(chat_id, f"Processing {file_name}...")
                else:
                    send_message(chat_id, "Invalid course number.")
            else:
                send_message(chat_id, "Failed to fetch courses.")
        else:
            send_message(chat_id, "Failed to update base URL.")

def main():
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            chat_id = update["message"]["chat"]["id"]
            text = update["message"].get("text", "").lower()
            process_command(chat_id, text)
        sleep(1)

if __name__ == "__main__":
    main()
