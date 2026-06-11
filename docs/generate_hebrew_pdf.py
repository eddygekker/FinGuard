"""
Generate FinGuard Hebrew PDF cheat sheet.
Run: py docs/generate_hebrew_pdf.py
"""

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "FinGuard-Hebrew-Guide.pdf"
FONT = Path(r"C:\Windows\Fonts\arial.ttf")


class HebrewPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_text_shaping(True)
        self.add_font("Arial", "", str(FONT))
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 18, 18)

    def rtl_cell(self, h: float, text: str, size: int = 11):
        self.set_x(self.l_margin)
        self.set_font("Arial", "", size)
        self.multi_cell(self.epw, h, text, align="R")

    def section_title(self, text: str):
        self.ln(3)
        self.set_x(self.l_margin)
        self.set_fill_color(239, 246, 255)
        self.set_font("Arial", "", 13)
        self.multi_cell(self.epw, 9, text, align="R", fill=True)
        self.ln(2)

    def bullet(self, text: str):
        self.rtl_cell(6, f"• {text}", size=10.5)


def build_pdf() -> None:
    pdf = HebrewPDF()
    pdf.add_page()

    pdf.set_x(pdf.l_margin)
    pdf.set_font("Arial", "", 22)
    pdf.multi_cell(pdf.epw, 12, "FinGuard", align="R")
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Arial", "", 14)
    pdf.multi_cell(pdf.epw, 8, "מדריך פרויקט - ניתוח נטישת לקוחות (Churn)", align="R")
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(pdf.epw, 6, "דף עזר להצגה בראיון / portfolio", align="R")
    pdf.ln(4)

    pdf.section_title("מה זה FinGuard?")
    pdf.rtl_cell(
        6,
        "פלטפורמת אנליטיקה לזיהוי לקוחות SaaS בסיכון לנטישה (Churn), "
        "הבנת הסיבות, וקבלת המלצות שימור - מבוסס SQL, Python, ML, React ו-AI.",
    )

    pdf.section_title("משפט pitch (30 שניות)")
    pdf.rtl_cell(
        6,
        "FinGuard מדמה 500 לקוחות SaaS ב-SQLite. מאמנים מודל Logistic Regression על שימוש, "
        "כרטיסי תמיכה וחיובים כדי לחזות נטישה. הדשבורד מציג חשבונות בסיכון לפי ציון סיכון ו-MRR. "
        "לכל לקוח - Retention Agent מייצר תוכנית שימור: למי להתקשר, מה לומר, ומה לעשות.",
    )

    pdf.section_title("ארכיטקטורה - 4 שכבות")
    pdf.bullet("שכבת נתונים: SQLite + SQL (סכמה ושאילתות)")
    pdf.bullet("שכבת ML: Python + scikit-learn - חיזוי נטישה וציון סיכון")
    pdf.bullet("Backend: Flask REST API - מטריקות, לקוחות, Agent")
    pdf.bullet("Frontend: React + Vite - דשבורד אינטראקטיבי")

    pdf.section_title("איך נוצרו הנתונים?")
    pdf.rtl_cell(
        6,
        "הנתונים סינתטיים (לא אמיתיים) - ריאליסטיים לדמו. הסקריפט data/seed_data.py "
        "יוצר 500 לקוחות עם היסטוריית שימוש, תמיכה וחיוב.",
    )
    pdf.bullet("~22% כבר נטשו (status = churned)")
    pdf.bullet("~78% פעילים: בריאים / סיכון בינוני / סיכון גבוה")
    pdf.bullet("תוכניות: Basic, Pro, Enterprise - עם MRR שונה")
    pdf.bullet("לכל לקוח: usage_events, support_tickets, billing_events")

    pdf.section_title("איפה הנתונים נמצאים?")
    pdf.bullet("קובץ DB: FinGuard/data/finguard.db (נוצר מקומית, לא ב-Git)")
    pdf.bullet("סכמה: sql/01_schema.sql")
    pdf.bullet("שאילתות: sql/02_analytics_queries.sql")
    pdf.bullet("אתחול: cd backend -> py scripts/init_db.py")

    pdf.section_title("טבלאות עיקריות")
    pdf.bullet("customers - חברה, תוכנית, MRR, סטטוס, תעשייה")
    pdf.bullet("usage_events - התחברויות, דקות פעילות, אימוץ פיצ'רים")
    pdf.bullet("support_tickets - פניות תמיכה (open / resolved)")
    pdf.bullet("billing_events - תשלומים, כשלונות, שדרוגים")
    pdf.bullet("customer_risk_scores - ציון סיכון, רמה, אותות (מחושב)")

    pdf.add_page()
    pdf.section_title("איך מחושב Churn Rate?")
    pdf.rtl_cell(
        6,
        "בדשבורד: (מספר לקוחות שנטשו ÷ סה\"כ לקוחות) × 100. "
        "לדוגמה: 127 נטשו מתוך 500 ≈ 25.4%. "
        "זה שיעור נטישה היסטורי כולל - לא רק החודש האחרון.",
    )

    pdf.section_title("ציון סיכון (ML)")
    pdf.rtl_cell(6, "מודל: Logistic Regression + StandardScaler. מטריקות: ROC-AUC ~0.94.")
    pdf.bullet("12 פיצ'רים: ירידת שימוש, ימים מהתחברות, כרטיסים פתוחים, כשלי תשלום, MRR, תוכנית ועוד")
    pdf.bullet("risk_score = הסתברות נטישה x 100 (0-100)")
    pdf.bullet("0-34: Low | 35-64: Medium | 65-100: High")
    pdf.bullet("קבצי מודל: backend/models/churn_model.joblib")

    pdf.section_title("מונחים בדשבורד")
    pdf.bullet("MRR - הכנסה חודשית חוזרת מהמנוי")
    pdf.bullet("MRR at risk - סכום MRR של לקוחות High risk בלבד")
    pdf.bullet("Signals - אזהרות: ירידת שימוש, כרטיסי תמיכה, כשל תשלום")
    pdf.bullet("Top risk drivers - מה דוחף את הציון (פסים = השפעה יחסית)")
    pdf.bullet("Open tickets = פניות תמיכה שעדיין לא נסגרו")

    pdf.section_title("Retention Agent (AI)")
    pdf.rtl_cell(
        6,
        "סוכן AI שמנתח לקוח נבחר ומחזיר: סיכום, למה בסיכון, פעולה מומלצת, "
        "צעדים, ונקודות לשיחה. מוגדר ב-backend/.env (Groq / Gemini / local).",
    )

    pdf.section_title("API עיקרי")
    pdf.bullet("GET /api/metrics - KPIs ו-churn rate")
    pdf.bullet("GET /api/customers - רשימת לקוחות + סינון סיכון")
    pdf.bullet("GET /api/customers/:id - Customer 360")
    pdf.bullet("POST /api/copilot/analyze - Retention Agent")

    pdf.section_title("הרצה")
    pdf.bullet("Backend: cd backend -> .venv -> py run.py -> localhost:5000")
    pdf.bullet("Frontend: cd frontend -> npm run dev -> localhost:5173")
    pdf.bullet("GitHub: github.com/eddygekker/FinGuard")

    pdf.section_title("מיומנויות לראיון")
    pdf.bullet("SQL - סכמה, JOINs, שאילתות אנליטיות")
    pdf.bullet("Python - הנדסת פיצ'רים, ML pipeline")
    pdf.bullet("Machine Learning - Logistic Regression, ROC-AUC")
    pdf.bullet("Full stack - Flask API + React UI")
    pdf.bullet("AI - LLM Agent עם playbook שימור")

    pdf.ln(6)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Arial", "", 9)
    pdf.multi_cell(pdf.epw, 5, "FinGuard | מדריך עברית | נוצר מהפרויקט", align="C")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT))
    print("Created:", OUTPUT)


if __name__ == "__main__":
    build_pdf()
