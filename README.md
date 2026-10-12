# MCA 2025-27 Batch – Semester 2 Result Analysis (CUTM) – Tableau

Interactive Tableau analysis of the **official Semester 2 results of the MCA 2025-27 batch** at Centurion University of
Technology and Management: 213 students, 5 subjects, 1,065 results.

**Open:** double-click `MCA_2025_Sem2_Result_Analysis.twbx` (Tableau Desktop or the free Tableau Reader). The data is packaged inside.

## Pages: 20 analysis sheets + 7 dashboards

Every chart is its own page (sheet tab), and the dashboards combine them:

### Dashboards (7)

| # | Dashboard | What it shows |
|---|---|---|
| 1 | **Overview** | KPIs (students, papers cleared, class SGPA, students with a backlog), grade distribution, how many students fall in each SGPA band |
| 2 | **Subject Analysis** | Toughest to easiest subject (average grade point), clearance rate per subject, grade mix per subject, backlogs per subject |
| 3 | **SGPA Analysis** | Every student ranked by SGPA, theory + practical vs theory + practical + project courses |
| 4 | **Student Profile** | Report card: choose any student (by code) to see the grade, grade point and credits in each subject and their SGPA |
| 5 | **Grade Heatmap** | Number of students with each grade in each subject (highlight table), credits vs average grade point |
| 6 | **Backlog Analysis** | How many backlogs students have (1 vs 2+), backlogs per subject, list of every result not cleared |
| 7 | **Consistency Analysis** | Weakest-subject grade vs SGPA for every student, students per SGPA band |

### Analysis sheets (20)

KPI Students, KPI Cleared, KPI SGPA, KPI Backlog, Grade Distribution, SGPA Bands, Subject Difficulty, Grade Mix by Subject,
Clearance by Subject, Course Type, Top Performers, Backlogs by Subject, Profile Grades, Profile Details, Profile Credits,
Grade Count Table, Credits vs Performance, Backlogs per Student, Backlog Students, Consistency.

## Key findings

- **94.9%** of papers cleared; **23 of 213** students have at least one paper not cleared.
- Class SGPA (credit-weighted) **7.87**; the top SGPA is **9.90**.
- **141 students (66%)** have SGPA 8 or above, while **16** are below 6.
- **Java Programming** is the toughest subject (average grade point 7.54, lowest clearance 92.5%); **Information Security** the best (8.15).
- Of the 23 students with backlogs, **11 have one** and **12 have two or more**; **125 students** scored A or better in every subject.
- **A** is the most common grade (455 of 1,065 results); there are 74 **O** grades.

## Data

`Datasets/mca_2025_sem2_results.csv`, made from the university result sheet by `scripts/prep_data.py`.

| Column | Meaning |
|---|---|
| Student | Anonymised code (STU-001 ... STU-213) |
| Batch, Semester | MCA 2025-27, Semester 2 |
| Subject Code, Subject Name, Subject | Course (Subject = short name for charts) |
| Course Type, Credit Split, Credits | T+P = Theory + Practical; TPP = Theory + Practical + Project; credits added up (e.g. 2.0+4.0 = 6) |
| Grade, Grade Label, Grade Point | O=10, E=9, A=8, B=7, C=6, D=5, F=0 |
| Result | Cleared (O-D) or Not Cleared |

**SGPA** = Σ(grade point × credits) / Σ(credits), computed in Tableau. Level-of-detail expressions give each student's SGPA and number of backlogs.

**Assumption:** grades **S, M and R** (34 results) are kept as they appear in the university sheet and are counted as
*not cleared* with grade point 0. If they mean something else, change `GP` in `scripts/prep_data.py` and rerun.

**Privacy:** names and registration numbers are **not** included. Each student is a code (STU-001 ...), so the workbook can be
shared safely. The original sheet stays in the private `_private` folder, which is never shared.

## Files

```
MCA2025_Result_Analysis/
├── MCA_2025_Sem2_Result_Analysis.twbx   Tableau workbook (share this file)
├── Datasets/mca_2025_sem2_results.csv   anonymised dataset
├── scripts/prep_data.py                 cleaning + anonymisation
├── scripts/build_real.py                workbook builder
├── _private/                            original university sheet (do not share)
└── README.md
```
