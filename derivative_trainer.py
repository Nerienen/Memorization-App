import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import random
import csv
import json
import os
import sys

# -------- Data Handling --------
QUESTIONS = {}
queue = []
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
        except:
            quiz_sets = {}
    else:
        quiz_sets = {}

def save_sets():
    with open(SETS_FILE, "w", encoding="utf-8") as f:
        json.dump(quiz_sets, f, indent=2)

def load_completion_counts():
    global set_completion_count
    if os.path.exists(COMPLETION_FILE):
        try:
            with open(COMPLETION_FILE, "r", encoding="utf-8") as f:
                set_completion_count = json.load(f)
        except:
            set_completion_count = {}
    else:
        set_completion_count = {}

def save_completion_counts():
    try:
        with open(COMPLETION_FILE, "w", encoding="utf-8") as f:
            json.dump(set_completion_count, f, indent=2)
    except Exception as e:
        print(f"Failed to save completion counts: {e}")

def load_questions_from_csv(file_path):
    questions = {}
    try:
        with open(file_path, newline='', encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    q = row[0].strip()
                    a = row[1].strip()
                    img = row[2].strip() if len(row) >= 3 else None
                    questions[q] = (a, img)
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
            json.dump(data, f)
    except Exception as e:
        print(f"Failed to save progress: {e}")

def clear_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()

# -------- Checkbox Panel (QA list) --------
# We'll populate checkbuttons inside qa_list_frame (a scrollable area)
def populate_qa_list():
    # clear the scrollable qa list frame
    clear_frame(qa_list_frame)
    global qa_vars, total_questions
    qa_vars = {}
    total_questions = 0

    # add checkbuttons
    for q, (a, _) in QUESTIONS.items():
        var = tk.BooleanVar(value=True)
        qa_vars[q] = var
        cb = tk.Checkbutton(qa_list_frame, text=f"{q} → {a}", variable=var, anchor="w", justify="left",
                            wraplength=middle_wrap_width - 20 if middle_wrap_width else 300,
                            command=lambda question=q: toggle_question(question))
        cb.pack(fill=tk.X, padx=5, pady=2)
        total_questions += 1

    # update progress bar maximum
    try:
        progress_bar["maximum"] = max(total_questions, 1)
        progress_text.config(text=f"{answered_count} / {total_questions}")
    except Exception:
        # UI not ready yet
        pass

def toggle_question(question):
    global total_questions, answered_count
    if qa_vars[question].get():  # checked → include
        if question not in answered_questions_set and (question, QUESTIONS[question]) not in queue:
            queue.append((question, QUESTIONS[question]))
            total_questions += 1
            progress_bar["maximum"] = max(total_questions, 1)
            progress_text.config(text=f"{answered_count} / {total_questions}")
    else:  # unchecked → remove
        queue[:] = [q_pair for q_pair in queue if q_pair[0] != question]
        wrong_queue[:] = [q_pair for q_pair in wrong_queue if q_pair[0] != question]
        if question in answered_questions_set:
            answered_questions_set.remove(question)
            answered_count -= 1
            progress_bar["value"] = answered_count
        total_questions = max(total_questions - 1, 0)
        progress_bar["maximum"] = max(total_questions, 1)
        progress_text.config(text=f"{answered_count} / {total_questions}")

# -------- Math Rendering --------
def render_math_latex(text, master, fontsize=16, color="black", max_width=8):
    fig, ax = plt.subplots(figsize=(max_width, 1))
    txt = ax.text(0.5, 0.5, text, fontsize=fontsize, ha='center', va='center', color=color, wrap=True)
    ax.axis('off')
    fig.canvas.draw()
    bbox = txt.get_window_extent(renderer=fig.canvas.get_renderer())
    width, height = bbox.width / fig.dpi, bbox.height / fig.dpi
    fig.set_size_inches(width * 1.05, height * 1.2)
    fig.tight_layout(pad=0.2)
    canvas = FigureCanvasTkAgg(fig, master=master)
    canvas.draw()
    widget = canvas.get_tk_widget()
    widget.pack()
    plt.close(fig)
    return widget

# -------- Quiz Logic --------
def reset_quiz(new_questions, progress_path):
    global QUESTIONS, queue, wrong_queue, current_question, options
    global answered_count, total_questions, answered_questions_set

    QUESTIONS = new_questions
    queue = list(QUESTIONS.items())
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
        # only re-add checked items from wrong_queue
        queue.extend([q_pair for q_pair in wrong_queue if qa_vars.get(q_pair[0], tk.BooleanVar(value=True)).get()])
        wrong_queue.clear()
        random.shuffle(queue)

    if not queue:
        show_completion()
        return

    current_question = queue.pop(0)
    func, (correct, image) = current_question

    if func not in answered_questions_set:
        answered_questions_set.add(func)
        answered_count += 1
        progress_bar["value"] = answered_count
        progress_text.config(text=f"{answered_count} / {total_questions}")
        if current_set:
            save_progress(quiz_sets[current_set]["progress"])

    # prepare options
    wrong_answers = random.sample(
        [v[0] for _, v in QUESTIONS.items() if v[0] != correct],
        min(3, len(QUESTIONS) - 1)
    )
    options = wrong_answers + [correct]
    random.shuffle(options)

    render_math_latex(rf" {func} ?", question_frame, fontsize=18, color="#165D66")

    if image:
        try:
            from PIL import Image, ImageTk
            import requests
            from io import BytesIO
            if image.startswith("http"):
                response = requests.get(image)
                img_data = BytesIO(response.content)
                img = Image.open(img_data)
            else:
                img = Image.open(image)
            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            img_label = tk.Label(question_frame, image=tk_img)
            img_label.image = tk_img
            img_label.pack(pady=10)
        except Exception as e:
            tk.Label(question_frame, text=f"[Image load failed: {e}]", fg="red").pack()

    for i, opt in enumerate(options):
        btn_widget = render_math_latex(opt, option_frames[i], fontsize=16)
        btn_widget.config(cursor="hand2")
        btn_widget.bind("<Button-1>", lambda e, o=opt: check_answer(o))

def check_answer(selected):
    func, (correct, image) = current_question
    clear_frame(feedback_frame)
    if selected == correct:
        render_math_latex(rf"✔ Correct, {func} → {correct}", feedback_frame, fontsize=18, color="green")
        log_progress(func, correct, True)
    else:
        render_math_latex(rf"✘ Wrong, {func} → {correct}", feedback_frame, fontsize=18, color="red")
        wrong_queue.append(current_question)
        log_progress(func, correct, False)
    feedback_frame.pack(pady=10)
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
    render_math_latex(r"$\text{All done!}$", question_frame, fontsize=16)
    tk.Label(question_frame, text=f"Completed {times_done} time(s)",
             font=("Arial", 12), fg="blue").pack(pady=5)
    tk.Button(question_frame, text="Retake", font=("Arial", 12), command=retake_quiz).pack(pady=10)
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
            os.rename(old_prog, new_prog)
        quiz_sets[new_name]["progress"] = new_prog
        save_sets()
        refresh_sets_list()

def refresh_sets_list():
    sets_list.delete(0, tk.END)
    for alias in quiz_sets:
        count = set_completion_count.get(alias, 0)
        display_name = f"{alias} ({count} done)" if count > 0 else alias
        sets_list.insert(tk.END, display_name)

def on_set_double_click(event):
    idx = sets_list.curselection()
    if idx:
        alias = sets_list.get(idx[0])
        switch_set(alias)

def on_set_right_click(event):
    idx = sets_list.curselection()
    if idx:
        alias = sets_list.get(idx[0])
        rename_set(alias)

def on_add_csv():
    file_path = filedialog.askopenfilename(title="Select CSV file",
                                           filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
    if file_path:
        add_csv(file_path)

# ------------------- GUI SETUP -------------------

root = tk.Tk()
root.title("Derivative Trainer")
root.state("zoomed")
try:
    root.attributes("-zoomed", True)
except:
    pass

# Menu
menubar = tk.Menu(root)
file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Load CSV...", command=on_add_csv)
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
tk.Button(bottom_frame, text="Next →", font=("Arial", 12), command=ask_question).pack()
bottom_frame.pack(pady=5)

# ---------------- Right side: two panels stuck together ----------------
right_frame = tk.Frame(container)
right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

# Middle: checkbox panel (scrollable)
middle_wrap_width = 320  # width used for wraplength calculation
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

progress_label = tk.Label(progress_frame, text="Progress", font=("Arial", 12, "bold"), bg="#f0f0f0")
progress_label.pack(pady=10)
progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=200, mode="determinate")
progress_bar.pack(pady=5)
progress_text = tk.Label(progress_frame, text="0 / 0", font=("Arial", 10), bg="#f0f0f0")
progress_text.pack(pady=5)
progress_inner = tk.Frame(progress_frame, bg="#f0f0f0")
progress_inner.pack(fill=tk.BOTH, expand=True)

sets_label = tk.Label(progress_frame, text="CSV Sets", font=("Arial", 12, "bold"), bg="#f0f0f0")
sets_label.pack(pady=5)
sets_list = tk.Listbox(progress_frame)
sets_list.pack(fill=tk.X, pady=5)
sets_list.bind("<Double-1>", on_set_double_click)
sets_list.bind("<Button-3>", on_set_right_click)

tk.Button(progress_frame, text="+ Add CSV", command=on_add_csv).pack(pady=5)
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
