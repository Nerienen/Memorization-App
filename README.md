# 📝 Personalizable MCQ Study App

After the downfall of personalized decks on **Memrise** and the lack of a straightforward, customizable application for studying with multiple-choice questions, I decided to build my own.

---

## 🚀 Features
- 📂 **Upload your own deck**: Just provide a `.csv` file.
- ❓ **Automatic MCQ generation** from your data.
- 📊 **Progress tracking** during each session (see which questions you miss the most).
- 🖼️ **Optional image support**: Add a third column with an image URL for visualization.
- 💾 **Progress saving across sessions**.

---

## 📂 CSV Format
Your `.csv` should follow this structure:

| Question           | Answer | Image (optional)               |
|-------------------|--------|--------------------------------|
| What is 2+2?       | 4      |                                |
| Capital of France? | Paris  | https://link.to/image.jpg      |

---

## ⚠️ Important Note
👉 Save your CSV as **UTF-8** for maximum compatibility (especially if it contains accents or special characters).

---

## 🛠️ Roadmap
- Improve UI/UX
- Add customizable quiz settings
