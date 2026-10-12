"""Clean the official CUTM result sheet (MCA 2025 batch, semester 2) for Tableau and anonymise it.
Names and registration numbers are replaced with codes (STU-001 ...) so the workbook can be shared."""
import sys
import pandas as pd

src = sys.argv[1] if len(sys.argv) > 1 else "raw.xlsx"
d = pd.read_excel(src, dtype=str)
GP = {"O": 10, "E": 9, "A": 8, "B": 7, "C": 6, "D": 5, "F": 0, "S": 0, "M": 0, "R": 0}
NAME = {"O": "O - Outstanding", "E": "E - Excellent", "A": "A - Very Good", "B": "B - Good", "C": "C - Average",
        "D": "D - Pass", "F": "F - Fail", "S": "S", "M": "M", "R": "R"}
SHORT = {"DATA STRUCTURES WITH COMPETITIVE CODING": "Data Structures", "JAVA PROGRAMMING": "Java Programming",
         "INFORMATION SECURITY (CISCO)": "Information Security", "CLOUD PRACTITIONER AWS": "Cloud (AWS)",
         "MACHINE LEARNING USING PYTHON": "Machine Learning (Python)"}
d["Grade"] = d["Grade"].str.strip().str.upper()
ids = {r: f"STU-{i + 1:03d}" for i, r in enumerate(sorted(d["Reg_No"].unique()))}
out = pd.DataFrame({
    "Student": d["Reg_No"].map(ids),
    "Batch": "MCA 2025-27",
    "Semester": 2,
    "Subject Code": d["Subject_Code"],
    "Subject Name": d["Subject_Name"].str.title().str.replace("Aws", "AWS").str.replace("(Cisco)", "(CISCO)", regex=False),
    "Subject": d["Subject_Name"].map(SHORT).fillna(d["Subject_Name"].str.title()),
    "Course Type": d["Type"].map({"T+P": "Theory + Practical", "TPP": "Theory + Practical + Project"}).fillna(d["Type"]),
    "Credit Split": d["Credits"],
    "Credits": d["Credits"].str.split("+").apply(lambda p: sum(float(x) for x in p)),
    "Grade": d["Grade"],
    "Grade Label": d["Grade"].map(NAME).fillna(d["Grade"]),
    "Grade Point": d["Grade"].map(GP).fillna(0).astype(int),
    "Result": d["Grade"].map(lambda g: "Cleared" if g in "OEABCD" else "Not Cleared"),
})
out.to_csv("mca_2025_sem2_results.csv", index=False)
s = out.assign(w=out["Grade Point"] * out.Credits).groupby("Student").apply(lambda g: g.w.sum() / g.Credits.sum())
print(out.shape, "students", out.Student.nunique())
print("cleared papers", round((out.Result == "Cleared").mean(), 3), "| students with a not-cleared paper",
      out[out.Result == "Not Cleared"].Student.nunique())
print("class SGPA (credit-weighted)", round((out["Grade Point"] * out.Credits).sum() / out.Credits.sum(), 2),
      "| mean student SGPA", round(s.mean(), 2), "| max", round(s.max(), 2))
print(out.groupby("Subject")["Grade Point"].mean().round(2).sort_values())
print(pd.cut(s, [0, 6, 7, 8, 9, 10.01], right=False).value_counts().sort_index())
