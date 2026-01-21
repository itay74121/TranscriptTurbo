# PROCESS.md - תיעוד תהליך הפיתוח

## 1. תכנון המערכת

**הדרישות:**
- העלאת אודיו → תמלול (Speechmatics) → סיכום מובנה (OpenAI) → ייצוא ל-Word
- חילוץ: משתתפים, החלטות, action items

**החלטות ארכיטקטוריות:**
- הפרדת endpoints: `/transcribe` ו-`/summarize` (גמישות)
- Pydantic models לולידציה
- Error handling מובנה (BadRequestError, UpstreamError, etc.)
- קונפיגורציה דרך env vars

**מבנה:**
```
backend/app/
  ├── api/routes/     # Endpoints
  ├── services/       # Speechmatics, OpenAI
  ├── utils/          # Audio trim, DOCX builder
  ├── core/           # Config, errors
  └── prompts/        # System prompts
```

---

## 2. שימוש ב-AI בתהליך הפיתוח

**הגישה:** השתמשתי ב-AI לתכנון וייעוץ טכני. שאלתי שאלות ספציפיות על ארכיטקטורה, patterns, ופתרון בעיות. כל קוד נבדק, הובן, ומותאם לצרכים הספציפיים של הפרויקט.

**דוגמאות לפרומפטים:**

1. **תכנון ארכיטקטורה:**
   - "איך לארגן FastAPI לתמלול וסיכום? איזה patterns? איך לטפל בשגיאות מ-upstream APIs?"
   - **תוצאה:** מבנה מודולרי, Pydantic, מחלקות שגיאות מותאמות

2. **System Prompt:**
   - "איך לכתוב prompt שמסוכם פגישות? איך למנוע hallucinations? איך להבטיח שהמודל לא ימציא משתתפים?"
   - **תוצאה:** Prompt מפורט עם דוגמאות, הדגשות על accuracy, טיפול ב-edge cases

3. **Speaker Diarization:**
   - "איך לקבץ מילים לפי speaker? מה אם אין diarization?"
   - **תוצאה:** אלגוריתם עם fallback

4. **Frontend State:**
   - "איך לנהל state מורכב (קובץ, תמלול, סיכום, היסטוריה, גרסאות)?"
   - **תוצאה:** useState hooks, localStorage abstraction, file hash לזיהוי

**עקרונות:**
- שאלות ממוקדות ("איך לטפל ב-X במקרה של Y?")
- בדיקה והבנה של כל קוד
- איטרציות עד פתרון אופטימלי
- שילוב עם best practices

---

## 3. בעיות ופתרונות

### JSON Schema Validation
**בעיה:** OpenAI החזיר שדות לא נכונים  
**פתרון:** שימוש ב-`json_schema` עם `strict: true` - המודל מחויב ל-schema מדויק

### Speaker Diarization
**בעיה:** לא תמיד זמין (תלוי ב-plan)  
**פתרון:** Fallback logic - ניסיון JSON, אם נכשל חזרה ל-plain text, default speaker אם חסר

### Frontend State Management
**בעיה:** הרבה state variables → bugs של state לא מסונכרן  
**פתרון:** פונקציות מובנות, state updates atomic, useEffect לסנכרון

### Audio Trimming
**בעיה:** תמיכה גם ב-frontend (FFmpeg.wasm) וגם ב-backend (VAD)  
**פתרון:** Flag `frontend_trimmed` - אם true, backend לא מנסה לחתוך שוב

### History עם Multiple Versions
**בעיה:** איך לאחסן מספר גרסאות של סיכום?  
**פתרון:** `summaries: SummaryVersion[]` - array של גרסאות, כל סיכום חדש = version חדש

---

## 4. מה אנחנו מחפשים

### שימוש חכם ב-AI
השתמשתי ב-AI ככלי עזר לתכנון וייעוץ. שאלתי שאלות ממוקדות, הבנתי את התשובות, והתאמתי אותן לצרכים הספציפיים. שילבתי את הייעוץ עם ידע קיים ו-best practices.

**דוגמה:** כשתכננתי את ה-System Prompt, שאלתי שאלות המשך: "איך למנוע hallucinations?", "מה אם אין action items?" - זה הוביל ל-prompt מדויק יותר דרך איטרציות.

### חשיבה עצמאית
הבנתי את ה-brief, פירקתי את הבעיה לחלקים, וקיבלתי החלטות ארכיטקטוריות בעצמי.

**דוגמה:** החלטתי בעצמי ליצור endpoints נפרדים ל-transcribe ו-summarize, למרות שהדרישה הראשונית הייתה רק endpoint אחד.

### System Prompt איכותי
- ברור ומפורט
- עם דוגמאות (חיוביות ושליליות)
- מטפל ב-edge cases
- מונע hallucinations - הדגשה מפורשת

---

## 5. זמן פיתוח

**סה"כ:** ~6 שעות

**פירוק:**
- תכנון: 1.5 שעות
- Backend core: 3 שעות
- Speechmatics: 2 שעות
- OpenAI + System Prompt: 2.5 שעות (איטרציות רבות!)
- Frontend: 3 שעות
- Testing & Debugging: 2 שעות
- Documentation: 1 שעה

---

## 6. System Prompt - למה בניתי אותו ככה

**הפרומפט המלא:** `backend/app/prompts/meeting_summary_system.txt`

### עקרונות עיצוב:

1. **מבנה היררכי** - LLMs עובדים טוב יותר עם הנחיות מובנות, כל קטגוריה עם הסבר נפרד

2. **דוגמאות קונקרטיות** - לכל קטגוריה יש דוגמאות של מה נכון ומה לא. דוגמאות שליליות חשובות במיוחד

3. **הדגשה על Accuracy** - כלל #1: "Accuracy First", כלל #3: "No Hallucination". הדגשה חוזרת: "Do not invent, infer, or assume"

4. **הבחנה בין קטגוריות** - Note מפורש: "Conclusions are different from decisions" + דוגמאות לכל אחד

5. **טיפול ב-Participants** - זה המקום הכי נפוץ ל-hallucinations. דוגמאות שליליות מפורשות: "If someone says 'John mentioned that...' but John never speaks, do NOT include John"

6. **Empty Arrays תקין** - כלל #2: "Empty Arrays for Missing Data". חשוב להבהיר ש-empty array זה תקין, לא שגיאה

7. **Edge Cases** - כלל #5: תמליל קצר/ריק, טקסט לא ברור, speaker labels לא ברורים

8. **Null Values** - "If owner/due_date not mentioned, set to null. Do not infer or guess"

### איטרציות:

1. **גרסה בסיסית** → המודל המציא משתתפים → הוספתי סעיף מפורט עם דוגמאות שליליות
2. **הוספתי הבחנה conclusions/decisions** → עדיין בלבל → הוספתי note מפורש
3. **הוספתי null values** → ניסה לנחש → הדגשה "Do not infer or guess"
4. **הוספתי edge cases** → תמלילים קצרים גרמו לשגיאות → כלל #5
5. **הוספתי Critical Rules** → התעלם מהנחיות → ריכזתי כללים חשובים ב-section נפרד

**תוצאה:** Prompt שנותן תוצאות מדויקות, עקביות, שימושיות ואמינות.

---

## 7. לקחים

- **System Prompt זה אמנות** - צריך איטרציות, דוגמאות, והדגשות
- **AI זה כלי, לא תחליף** - צריך להבין ולבדוק
- **Edge cases חשובים** - לחשוב עליהם מראש
- **ארכיטקטורה נכונה חוסכת זמן** - השקעה בתכנון משתלמת
