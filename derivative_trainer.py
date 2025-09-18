import tkinter as tk
from tkinter import filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import random
import csv

# -------- Data Handling --------
QUESTIONS = {}
queue = []
wrong_queue = []
current_question = None
options = []

def load_questions_from_csv(file_path):
    """Load questions from a CSV file with question, answer, optional image."""
    questions = {}
    try:
        with open(file_path, newline='', encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    q = row[0].strip()
                    a = row[1].strip()
                    img = row[2].strip() if len(row) >= 3 else None
                    questions[q] = (a, img)   # store as tuple (answer, image)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load CSV:\n{e}")
        return {}
    return questions

def reset_quiz(new_questions):
    global QUESTIONS, queue, wrong_queue, current_question, options
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

    if QUESTIONS:
        ask_question()

# -------- Math Rendering --------
def render_math_latex(text, master, fontsize=16, color="black", max_width=8):
    """Render text (LaTeX or plain) in a Tk frame with auto-scaling width/height."""
    fig, ax = plt.subplots(figsize=(max_width, 1))
    txt = ax.text(0.5, 0.5, text, fontsize=fontsize,
                  ha='center', va='center', color=color, wrap=True)
    ax.axis('off')

    # Autoscale figure to fit text
    fig.canvas.draw()
    bbox = txt.get_window_extent(renderer=fig.canvas.get_renderer())
    width, height = bbox.width / fig.dpi, bbox.height / fig.dpi
    fig.set_size_inches(width * 1.1, height * 1.2)  # add padding
    fig.tight_layout(pad=0.2)

    canvas = FigureCanvasTkAgg(fig, master=master)
    canvas.draw()
    widget = canvas.get_tk_widget()
    widget.pack()
    return widget

def clear_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()

# -------- Quiz Logic --------
def ask_question():
    global current_question, options
    feedback_frame.pack_forget()
    bottom_frame.pack_forget()
    clear_frame(question_frame)
    for btn in option_frames:
        clear_frame(btn)

    if not queue and not wrong_queue:
        render_math_latex(r"$\text{All done!}$", question_frame, fontsize=20)
        return

    if not queue and wrong_queue:
        queue.extend(wrong_queue)
        wrong_queue.clear()
        random.shuffle(queue)

    current_question = queue.pop(0)
    func, (correct, image) = current_question  # unpack (answer, image)

    # Wrong answers
    wrong_answers = random.sample(
        [v[0] for _, v in QUESTIONS.items() if v[0] != correct],
        min(3, len(QUESTIONS) - 1)
    )
    options = wrong_answers + [correct]
    random.shuffle(options)

    # Show question text
    render_math_latex(rf" {func} ?", question_frame, fontsize=20)

    # Show optional image
    if image:
        try:
            from PIL import Image, ImageTk
            import requests
            from io import BytesIO

            if image.startswith("http"):  # URL
                response = requests.get(image)
                img_data = BytesIO(response.content)
                img = Image.open(img_data)
            else:  # local file
                img = Image.open(image)

            # Scale image with preserved aspect ratio
            max_size = (800, 800)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            tk_img = ImageTk.PhotoImage(img)
            img_label = tk.Label(question_frame, image=tk_img)
            img_label.image = tk_img  # keep reference alive
            img_label.pack(pady=10)

        except Exception as e:
            tk.Label(question_frame, text=f"[Image load failed: {e}]",
                     fg="red").pack()

    # Show answer options
    for i, opt in enumerate(options):
        btn_widget = render_math_latex(opt, option_frames[i], fontsize=16)
        btn_widget.config(cursor="hand2")
        btn_widget.bind("<Button-1>", lambda e, o=opt: check_answer(o))

def check_answer(selected):
    func, (correct, image) = current_question  # unpack correctly
    clear_frame(feedback_frame)
    if selected == correct:
        render_math_latex(rf"✔ Correct, {func} → {correct}", feedback_frame,
                          fontsize=18, color="green")
        log_progress(func, correct, True)
    else:
        render_math_latex(rf"✘ Wrong, {func} → {correct}", feedback_frame,
                          fontsize=18, color="red")
        wrong_queue.append(current_question)
        log_progress(func, correct, False)

    feedback_frame.pack(pady=10)
    bottom_frame.pack(pady=5)

# -------- Progress Panel --------
def log_progress(question, answer, correct_flag):
    color = "green" if correct_flag else "red"
    entry_label = tk.Label(
        progress_inner,
        text=f"{question} → {answer}",
        fg=color,
        bg="#f0f0f0",
        anchor="w",
        justify="left",
        wraplength=220
    )
    entry_label.pack(pady=2, anchor="w")

# -------- GUI Setup --------
root = tk.Tk()
root.title("Derivative Trainer")
root.state("zoomed")
try:
    root.attributes("-zoomed", True)
except:
    pass

# Menu bar
menubar = tk.Menu(root)
file_menu = tk.Menu(menubar, tearoff=0)
def open_csv():
    file_path = filedialog.askopenfilename(
        title="Select CSV file",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if file_path:
        new_q = load_questions_from_csv(file_path)
        if new_q:
            reset_quiz(new_q)

file_menu.add_command(label="Load CSV...", command=open_csv)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=file_menu)
root.config(menu=menubar)

# -------- Scrollable root container --------
main_canvas = tk.Canvas(root, highlightthickness=0)
main_canvas.pack(fill=tk.BOTH, expand=True)

scrollbar = tk.Scrollbar(root, orient="vertical", command=main_canvas.yview)
scrollbar.pack(side=tk.RIGHT, fill="y")
main_canvas.configure(yscrollcommand=scrollbar.set)

outer_frame = tk.Frame(main_canvas)
main_canvas.create_window((0, 0), window=outer_frame, anchor="nw")

outer_frame.bind(
    "<Configure>",
    lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
)

# Mousewheel scrolling
def _on_mousewheel(event):
    main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
main_canvas.bind_all("<Button-4>", lambda e: main_canvas.yview_scroll(-1, "units"))
main_canvas.bind_all("<Button-5>", lambda e: main_canvas.yview_scroll(1, "units"))

# -------- Layout inside outer_frame --------
# Left quiz area
main_frame = tk.Frame(outer_frame)
main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

question_frame = tk.Frame(main_frame)
question_frame.pack(pady=20)

option_frames = []
for _ in range(4):
    frame = tk.Frame(main_frame)
    frame.pack(pady=5)
    option_frames.append(frame)

feedback_frame = tk.Frame(main_frame)

bottom_frame = tk.Frame(main_frame)
next_button = tk.Button(bottom_frame, text="Next →",
                        font=("Arial", 12), command=ask_question)
next_button.pack()

# Right progress panel
progress_frame = tk.Frame(outer_frame, width=250, bg="#f0f0f0")
progress_frame.pack(side=tk.RIGHT, fill=tk.Y)

progress_label = tk.Label(progress_frame, text="Progress",
                          font=("Arial", 12, "bold"), bg="#f0f0f0")
progress_label.pack(pady=10)

progress_inner = tk.Frame(progress_frame, bg="#f0f0f0")
progress_inner.pack(fill=tk.BOTH, expand=True)

# -------- Start --------
root.mainloop()
