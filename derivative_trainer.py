import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, simpledialog, ttk
import matplotlib.pyplot as plt  # kept (not required for current text rendering)
import random
import csv
import json
import os
import sys

# -------- Config / Font / CJK preference --------
CJK_FONTS = [
    "Microsoft YaHei, 14", "SimHei", "Noto Sans CJK SC",
    "Noto Sans CJK JP", "PingFang SC", "Heiti SC",
    "Arial Unicode MS"
]

# -------- Data Handling --------
QUESTIONS = {}                # mapping: chinese -> (english, pinyin)
queue = []                    # list of (chinese, (english, pinyin))
wrong_queue = []
current_question = None
options = []

# Progress tracking
answered_count = 0
total_questions = 0
answered_questions_set = set()
set_completion_count = {}

qa_vars = {}  # dict to store BooleanVar for each question

BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
SETS_FILE = os.path.join(BASE_DIR, "quiz_sets.json")
PROGRESS_DIR = os.path.join(BASE_DIR, "progress_data")
COMPLETION_FILE = os.path.join(BASE_DIR, "completion_counts.json")
os.makedirs(PROGRESS_DIR, exist_ok=True)

quiz_sets = {}
current_set = None

# -------- Helper Functions --------
def load_sets():
    global quiz_sets
    if os.path.exists(SETS_FILE):
        try:
            with open(SETS_FILE, "r", encoding="utf-8") as f:
                quiz_sets = json.load(f)
        except Exception:
            quiz_sets = {}
    else:
        quiz_sets = {}

def save_sets():
    with open(SETS_FILE, "w", encoding="utf-8") as f:
        json.dump(quiz_sets, f, indent=2, ensure_ascii=False)

def load_completion_counts():
    global set_completion_count
    if os.path.exists(COMPLETION_FILE):
        try:
            with open(COMPLETION_FILE, "r", encoding="utf-8") as f:
                set_completion_count = json.load(f)
        except Exception:
            set_completion_count = {}
    else:
        set_completion_count = {}

def save_completion_counts():
    try:
        with open(COMPLETION_FILE, "w", encoding="utf-8") as f:
            json.dump(set_completion_count, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to save completion counts: {e}")

def load_questions_from_csv(file_path):
    """
    Expect CSV format:
      col0: Chinese (question)
      col1: Pinyin (hint)
      col2: English (answer)
    Returns a dict: { chinese: (english, pinyin), ... }
    """
    questions = {}
    try:
        with open(file_path, newline='', encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                # skip empty lines
                if not row or all(not cell.strip() for cell in row):
                    continue
                if len(row) >= 3:
                    chinese = row[0].strip()
                    pinyin = row[1].strip()
                    english = row[2].strip()
                    # if duplicate chinese entries, last one wins
                    questions[chinese] = (english, pinyin)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load CSV:\n{e}")
        return {}
    return questions

def save_progress(progress_path):
    data = {
        "answered_count": answered_count,
        "total_questions": total_questions,
        "answered_questions": list(answered_questions_set),
        "queue": [q for q, _ in queue],
        "wrong_queue": [q for q, _ in wrong_queue]
    }
    try:
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to save progress: {e}")

def clear_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()

# -------- Checkbox Panel (QA list) --------
middle_wrap_width = 320  # used for wraplength in QA checkbuttons

def populate_qa_list():
    clear_frame(qa_list_frame)
    global qa_vars, total_questions
    qa_vars = {}
    total_questions = 0

    for chinese, (english, pinyin) in QUESTIONS.items():
        var = tk.BooleanVar(value=True)
        qa_vars[chinese] = var
        # show Chinese (pinyin) -> english in the checkbox summary
        text = f"{chinese} ({pinyin}) → {english}"
        cb = tk.Checkbutton(qa_list_frame, text=text, variable=var, anchor="w", justify="left",
                            wraplength=middle_wrap_width - 20,
                            command=lambda question=chinese: toggle_question(question))
        cb.pack(fill=tk.X, padx=5, pady=2)
        total_questions += 1

    try:
        progress_bar["maximum"] = max(total_questions, 1)
        progress_text.config(text=f"{answered_count} / {total_questions}")
    except Exception:
        pass

def toggle_question(question):
    global total_questions, answered_count
    if qa_vars[question].get():
        if question not in answered_questions_set and (question, QUESTIONS[question]) not in queue:
            queue.append((question, QUESTIONS[question]))
            total_questions += 1
            progress_bar["maximum"] = max(total_questions, 1)
            progress_text.config(text=f"{answered_count} / {total_questions}")
    else:
        queue[:] = [q_pair for q_pair in queue if q_pair[0] != question]
        wrong_queue[:] = [q_pair for q_pair in wrong_queue if q_pair[0] != question]
        if question in answered_questions_set:
            answered_questions_set.remove(question)
            answered_count -= 1
            progress_bar["value"] = answered_count
        total_questions = max(total_questions - 1, 0)
        progress_bar["maximum"] = max(total_questions, 1)
        progress_text.config(text=f"{answered_count} / {total_questions}")

# -------- Text Rendering (CJK-safe) --------
def render_label(text, master, fontsize=16, color="black", wrap=800, bold=False):
    font_name = chosen_cjk if chosen_cjk else "Arial"
    font_style = (font_name, fontsize, "bold" if bold else "normal")
    lbl = tk.Label(master, text=text, font=font_style, fg=color, wraplength=wrap, justify="center")
    lbl.pack(pady=2)
    return lbl

# -------- Quiz Logic --------
def reset_quiz(new_questions, progress_path):
    global QUESTIONS, queue, wrong_queue, current_question, options
    global answered_count, total_questions, answered_questions_set

    QUESTIONS = new_questions
    queue = list(QUESTIONS.items())  # (chinese, (english, pinyin))
    random.shuffle(queue)
    wrong_queue = []
    current_question = None
    options = []

    clear_frame(question_frame)
    clear_frame(feedback_frame)
    for btn in option_frames:
        clear_frame(btn)
    clear_frame(progress_inner)

    answered_count = 0
    answered_questions_set = set()
    total_questions = len(new_questions)
    progress_bar["maximum"] = max(total_questions, 1)
    progress_bar["value"] = 0
    progress_text.config(text=f"0 / {total_questions}")

    # load saved progress if any
    if os.path.exists(progress_path):
        try:
            with open(progress_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                answered_questions_set = set(data.get("answered_questions", []))
                answered_count = len(answered_questions_set)
                progress_bar["value"] = answered_count
                progress_text.config(text=f"{answered_count} / {total_questions}")

                answered_set = set(data.get("answered_questions", []))
                queue = [(q, QUESTIONS[q]) for q, _ in queue if q not in answered_set]
                wrong_queue = [(q, QUESTIONS[q]) for q in data.get("wrong_queue", []) if q in QUESTIONS]
        except Exception as e:
            print(f"Failed to load progress: {e}")

    populate_qa_list()
    if QUESTIONS:
        ask_question()

def ask_question():
    global current_question, options, answered_count
    feedback_frame.pack_forget()
    bottom_frame.pack_forget()
    clear_frame(question_frame)
    for btn in option_frames:
        clear_frame(btn)

    # filter out unchecked
    queue[:] = [q_pair for q_pair in queue if qa_vars.get(q_pair[0], tk.BooleanVar(value=True)).get()]

    if answered_count >= total_questions:
        show_completion()
        return

    if not queue and wrong_queue:
        queue.extend([q_pair for q_pair in wrong_queue if qa_vars.get(q_pair[0], tk.BooleanVar(value=True)).get()])
        wrong_queue.clear()
        random.shuffle(queue)

    if not queue:
        show_completion()
        return

    current_question = queue.pop(0)
    chinese, (english, pinyin) = current_question

    if chinese not in answered_questions_set:
        answered_questions_set.add(chinese)
        answered_count += 1
        progress_bar["value"] = answered_count
        progress_text.config(text=f"{answered_count} / {total_questions}")
        if current_set:
            save_progress(quiz_sets[current_set]["progress"])

    # prepare options (english choices)
    all_english = [v[0] for _, v in QUESTIONS.items()]
    wrong_answers = []
    if len(all_english) > 1:
        candidates = [e for e in all_english if e != english]
        wrong_answers = random.sample(candidates, min(3, len(candidates)))
    options = wrong_answers + [english]
    random.shuffle(options)

    # display question: Chinese + pinyin
    render_label(chinese, question_frame, fontsize=28, color="#A11BCA", wrap=900, bold=True)
    render_label(pinyin, question_frame, fontsize=18, color="gray", wrap=900)

    # image support (if third column was used for image instead, but here we treat third as english)
    # show answer options as buttons
    for i, opt in enumerate(options):
        btn = tk.Button(option_frames[i], text=opt, font=(chosen_cjk, 14), width=36,
                        command=lambda o=opt: check_answer(o))
        btn.pack(pady=3, padx=5)

def check_answer(selected):
    chinese, (correct, pinyin) = current_question
    clear_frame(feedback_frame)
    if selected == correct:
        render_label(f"✔ Correct!  {chinese} — {pinyin} → {correct}", feedback_frame, fontsize=14, color="green")
        log_progress(chinese, correct, True)
    else:
        render_label(f"✘ Wrong.  {chinese} — {pinyin} → {correct}", feedback_frame, fontsize=14, color="red")
        wrong_queue.append(current_question)
        log_progress(chinese, correct, False)
    feedback_frame.pack(pady=8)
    bottom_frame.pack(pady=5)

def log_progress(question, answer, correct_flag):
    color = "green" if correct_flag else "red"
    entry_label = tk.Label(progress_inner, text=f"{question} → {answer}", fg=color, bg="#f0f0f0",
                           anchor="w", justify="left", wraplength=220)
    entry_label.pack(pady=2, anchor="w")

def show_completion():
    clear_frame(question_frame)
    clear_frame(feedback_frame)
    for btn in option_frames:
        clear_frame(btn)
    times_done = set_completion_count.get(current_set, 0)
    render_label("All done!", question_frame, fontsize=18, color="blue", bold=True)
    tk.Label(question_frame, text=f"Completed {times_done} time(s)", font=(chosen_cjk, 12), fg="blue").pack(pady=5)
    tk.Button(question_frame, text="Retake", font=(chosen_cjk, 12), command=retake_quiz).pack(pady=10)
    refresh_sets_list()
    save_completion_counts()

def retake_quiz():
    global queue, wrong_queue, answered_count, answered_questions_set
    if current_set not in set_completion_count:
        set_completion_count[current_set] = 1
    else:
        set_completion_count[current_set] += 1
    save_completion_counts()
    refresh_sets_list()
    answered_count = 0
    answered_questions_set = set()
    queue = list(QUESTIONS.items())
    random.shuffle(queue)
    wrong_queue = []
    progress_bar["value"] = 0
    progress_text.config(text=f"0 / {total_questions}")
    clear_frame(progress_inner)
    ask_question()

# -------- CSV Manager --------
def add_csv(file_path):
    global current_set
    alias = os.path.splitext(os.path.basename(file_path))[0]
    if alias in quiz_sets:
        i = 2
        while f"{alias}_{i}" in quiz_sets:
            i += 1
        alias = f"{alias}_{i}"
    quiz_sets[alias] = {
        "path": file_path,
        "progress": os.path.join(PROGRESS_DIR, alias + ".json")
    }
    save_sets()
    refresh_sets_list()
    switch_set(alias)

def remove_csv(alias):
    # alias passed expected to be the raw key
    if alias in quiz_sets:
        prog = quiz_sets[alias].get("progress")
        # remove progress file if exists
        try:
            if prog and os.path.exists(prog):
                os.remove(prog)
        except Exception:
            pass
        del quiz_sets[alias]
        save_sets()
        refresh_sets_list()
        # if the removed set was active, clear UI
        global current_set, QUESTIONS, queue, answered_count, answered_questions_set, total_questions
        if current_set == alias:
            current_set = None
            QUESTIONS = {}
            queue = []
            answered_count = 0
            answered_questions_set = set()
            total_questions = 0
            progress_bar["value"] = 0
            progress_text.config(text=f"0 / 0")
            set_label.config(text="Active: None")
            clear_frame(question_frame)
            clear_frame(qa_list_frame)

def switch_set(alias):
    global current_set
    if " (" in alias:
        alias = alias.split(" (")[0]
    current_set = alias
    file_path = quiz_sets[alias]["path"]
    new_q = load_questions_from_csv(file_path)
    if new_q:
        reset_quiz(new_q, quiz_sets[alias]["progress"])
    set_label.config(text=f"Active: {alias}")
    refresh_sets_list()

def rename_set(alias):
    if " (" in alias:
        alias = alias.split(" (")[0]
    new_name = simpledialog.askstring("Rename Set", f"Enter new name for '{alias}':")
    if new_name and new_name not in quiz_sets:
        quiz_sets[new_name] = quiz_sets.pop(alias)
        old_prog = quiz_sets[new_name]["progress"]
        new_prog = os.path.join(PROGRESS_DIR, new_name + ".json")
        if os.path.exists(old_prog):
            try:
                os.rename(old_prog, new_prog)
            except Exception:
                pass
        quiz_sets[new_name]["progress"] = new_prog
        save_sets()
        refresh_sets_list()

def refresh_sets_list():
    # We'll show each set as a row with label (clickable) and a red X button
    clear_frame(sets_items_frame)
    for alias in quiz_sets:
        count = set_completion_count.get(alias, 0)
        display_name = f"{alias} ({count} done)" if count > 0 else alias
        row = tk.Frame(sets_items_frame)
        row.pack(fill=tk.X, pady=2, padx=2)

        btn_label = tk.Button(row, text=display_name, anchor="w",
                              command=lambda a=alias: switch_set(a))
        btn_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        remove_btn = tk.Button(row, text="✖", fg="white", bg="red",
                               command=lambda a=alias: remove_csv(a))
        remove_btn.pack(side=tk.RIGHT, padx=(3,0))

def on_add_csv():
    file_path = filedialog.askopenfilename(title="Select CSV file",
                                           filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
    if file_path:
        add_csv(file_path)

def on_remove_selected_csv():
    # remove currently active set
    if current_set:
        if messagebox.askyesno("Remove CSV", f"Remove set '{current_set}'?"):
            remove_csv(current_set)

# ------------------- GUI SETUP & Font Init -------------------
root = tk.Tk()
root.title("Chinese Flashcard Trainer")
# try maximize
try:
    root.state("zoomed")
except Exception:
    pass
try:
    root.attributes("-zoomed", True)
except Exception:
    pass

# Font / CJK init: choose a CJK-capable font if available
available_families = list(tkfont.families())
chosen = None
for f in CJK_FONTS:
    if f in available_families:
        chosen = f
        break
if not chosen:
    chosen = available_families[0] if available_families else "Arial"
chosen_cjk = chosen
# Apply as default
root.option_add("*Font", f"{chosen_cjk} 11")

# Menu
menubar = tk.Menu(root)
file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Load CSV...", command=on_add_csv)
file_menu.add_command(label="Remove Active CSV", command=on_remove_selected_csv)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=file_menu)
root.config(menu=menubar)

# Main container
container = tk.Frame(root)
container.pack(fill=tk.BOTH, expand=True)

# ---------------- Left: Quiz Area (scrollable) ----------------
main_canvas = tk.Canvas(container, highlightthickness=0)
main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar = tk.Scrollbar(container, orient="vertical", command=main_canvas.yview)
scrollbar.pack(side=tk.LEFT, fill="y")
main_canvas.configure(yscrollcommand=scrollbar.set)
outer_frame = tk.Frame(main_canvas)
main_canvas.create_window((0,0), window=outer_frame, anchor="nw")
outer_frame.bind("<Configure>", lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))

def _on_mousewheel(event):
    main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
main_canvas.bind_all("<Button-4>", lambda e: main_canvas.yview_scroll(-1, "units"))
main_canvas.bind_all("<Button-5>", lambda e: main_canvas.yview_scroll(1, "units"))

# Quiz content inside outer_frame
quiz_frame = tk.Frame(outer_frame)
quiz_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

question_frame = tk.Frame(quiz_frame)
question_frame.pack(pady=20)

option_frames = []
for _ in range(4):
    frame = tk.Frame(quiz_frame)
    frame.pack(pady=5)
    option_frames.append(frame)

feedback_frame = tk.Frame(quiz_frame)
bottom_frame = tk.Frame(quiz_frame)
tk.Button(bottom_frame, text="Next →", font=(chosen_cjk, 12), command=ask_question).pack()
bottom_frame.pack(pady=5)

# ---------------- Right side: panels ----------------
right_frame = tk.Frame(container)
right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

# Middle: QA list (scrollable)
middle_wrap = tk.Frame(right_frame, bd=1, relief="sunken", width=middle_wrap_width)
middle_wrap.pack(side=tk.LEFT, fill=tk.Y, padx=(5,3), pady=5)

qa_canvas = tk.Canvas(middle_wrap, highlightthickness=0, width=middle_wrap_width)
qa_scrollbar = tk.Scrollbar(middle_wrap, orient="vertical", command=qa_canvas.yview)
qa_canvas.configure(yscrollcommand=qa_scrollbar.set)
qa_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
qa_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

qa_list_frame = tk.Frame(qa_canvas)
qa_canvas.create_window((0, 0), window=qa_list_frame, anchor="nw")
qa_list_frame.bind("<Configure>", lambda e: qa_canvas.configure(scrollregion=qa_canvas.bbox("all")))

# Progress panel (rightmost)
progress_frame = tk.Frame(right_frame, width=300, bg="#f0f0f0")
progress_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(3,5), pady=5)

progress_label = tk.Label(progress_frame, text="Progress", font=(chosen_cjk, 12, "bold"), bg="#f0f0f0")
progress_label.pack(pady=10)
progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=200, mode="determinate")
progress_bar.pack(pady=5)
progress_text = tk.Label(progress_frame, text="0 / 0", font=(chosen_cjk, 10), bg="#f0f0f0")
progress_text.pack(pady=5)
progress_inner = tk.Frame(progress_frame, bg="#f0f0f0")
progress_inner.pack(fill=tk.BOTH, expand=True)

sets_label = tk.Label(progress_frame, text="CSV Sets", font=(chosen_cjk, 12, "bold"), bg="#f0f0f0")
sets_label.pack(pady=5)

# container for sets rows (each row = button + red remove)
sets_items_frame = tk.Frame(progress_frame, bg="#f0f0f0")
sets_items_frame.pack(fill=tk.X, pady=(0,5))

tk.Button(progress_frame, text="+ Add CSV", command=on_add_csv).pack(pady=5)
tk.Button(progress_frame, text="❌ Remove Active CSV", fg="white", bg="red", command=on_remove_selected_csv).pack(pady=2)

set_label = tk.Label(progress_frame, text="Active: None", bg="#f0f0f0")
set_label.pack(pady=5)

# ---------------- Initialize ----------------
load_sets()
load_completion_counts()
refresh_sets_list()
if quiz_sets:
    first_alias = next(iter(quiz_sets))
    switch_set(first_alias)

root.mainloop()
