import uuid, random, string, zipfile, os
import pandas as pd
from xml.sax.saxutils import escape, quoteattr

CSV = "mca_2025_sem2_results.csv"
df = pd.read_csv(CSV)
DS = "federated." + "".join(random.Random(1).choices(string.ascii_lowercase + string.digits, k=28))
TS = "textscan." + "".join(random.Random(2).choices(string.ascii_lowercase + string.digits, k=28))
OBJ = "mca_2025_sem2_results.csv_" + uuid.UUID(int=random.Random(3).getrandbits(128)).hex.upper()
CAP = "mca_2025_sem2_results"
U = lambda: "{" + str(uuid.uuid4()).upper() + "}"
A = lambda s: quoteattr(s)          # attribute with quotes

TYPES = {"object": "string", "str": "string", "string": "string", "int64": "integer", "float64": "real"}
cols = [(c, TYPES[str(t)]) for c, t in df.dtypes.items()]
REMOTE = {"string": 129, "integer": 20, "real": 5}
AGG = {"string": "Count", "integer": "Sum", "real": "Sum"}

CALCS = {
    "Calculation_1001": ("Cleared Flag", "integer", "measure", "quantitative", "IF [Result] = 'Cleared' THEN 1 ELSE 0 END", "p0.0%"),
    "Calculation_1003": ("SGPA", "real", "measure", "quantitative", "SUM([Grade Point] * [Credits]) / SUM([Credits])", "n0.00"),
    "Calculation_1007": ("Students with Backlog", "integer", "measure", "quantitative", "COUNTD(IF [Result] = 'Not Cleared' THEN [Student] END)", "n0"),
    "Calculation_2002": ("Is Selected Student", "boolean", "dimension", "nominal", "[Student] = [Parameters].[Parameter 1]", None),
    "Calculation_2004": ("Student SGPA", "real", "measure", "quantitative", "{FIXED [Student] : SUM([Grade Point] * [Credits]) / SUM([Credits])}", "n0.00"),
    "Calculation_2006": ("Backlogs per Student", "integer", "dimension", "ordinal",
                         "{FIXED [Student] : SUM(IF [Result] = 'Not Cleared' THEN 1 ELSE 0 END)}", None),
    "Calculation_2005": ("SGPA Band", "string", "dimension", "nominal",
                         "IF [Calculation_2004] >= 9 THEN '9 - 10' ELSEIF [Calculation_2004] >= 8 THEN '8 - 9' "
                         "ELSEIF [Calculation_2004] >= 7 THEN '7 - 8' ELSEIF [Calculation_2004] >= 6 THEN '6 - 7' ELSE 'Below 6' END", None),
}
CAPTION = {k: v[0] for k, v in CALCS.items()}
DIMS_ORDINAL = {"Semester", "Calculation_2006"}
PARAM_COL = "[Parameter 1]"


def col_def(name):
    if name in CALCS:
        cap, dt, role, typ, f, fmt = CALCS[name]
        fm = f" default-format={A(fmt)}" if fmt else ""
        return (f"<column caption={A(cap)} datatype={A(dt)}{fm} name={A('[' + name + ']')} role={A(role)} type={A(typ)}>"
                f"<calculation class='tableau' formula={A(f)} /></column>")
    dt = dict(cols)[name]
    fmt = {"Grade Point": "n0.00", "Credits": "n0"}.get(name)
    if fmt:
        return f"<column datatype={A(dt)} default-format={A(fmt)} name={A('[' + name + ']')} role='measure' type='quantitative' />"
    if name in DIMS_ORDINAL:
        return f"<column datatype={A(dt)} name={A('[' + name + ']')} role='dimension' type='ordinal' />"
    role, typ = ("dimension", "nominal") if dt == "string" else ("measure", "quantitative")
    return f"<column datatype={A(dt)} name={A('[' + name + ']')} role={A(role)} type={A(typ)} />"


def inst(field, how):
    """Return (instance name inside the datasource, xml for dependencies)."""
    if field == "__records__":
        n = f"[__tableau_internal_object_id__].[cnt:{OBJ}:qk]"
        x = (f"<column-instance column={A('[__tableau_internal_object_id__].[' + OBJ + ']')} derivation='Count' name={A(n)} pivot='key' type='quantitative' />"
             f"<column caption='Results' datatype='table' name={A('[__tableau_internal_object_id__].[' + OBJ + ']')} role='measure' type='quantitative' />")
        return n, x
    pre = {"none": "none", "avg": "avg", "sum": "sum", "ctd": "ctd", "usr": "usr", "min": "min"}[how]
    der = {"none": "None", "avg": "Avg", "sum": "Sum", "ctd": "CountD", "usr": "User", "min": "Min"}[how]
    if how == "none":
        typ = "ordinal" if field in DIMS_ORDINAL else "nominal"
        suf = "ok" if typ == "ordinal" else "nk"
    else:
        typ, suf = "quantitative", "qk"
    n = f"[{pre}:{field}:{suf}]"
    x = col_def(field) + f"<column-instance column={A('[' + field + ']')} derivation={A(der)} name={A(n)} pivot='key' type={A(typ)} />"
    return n, x


def q(n):
    return f"[{DS}].{n}"


def sheet(name, title, rows=(), cols_=(), mark="Automatic", color=None, text=None, detail=(), sort=None, label=True,
          kpi_caption=None, filters="", axis=None, selected_only=False, not_cleared_only=False):
    deps, seen = [], set()
    def use(f, how):
        n, x = inst(f, how)
        if n not in seen:
            seen.add(n); deps.append(x)
        return q(n)
    param_ds, param_dep = "", ""
    if selected_only:
        fn = use("Calculation_2002", "none")

        filters += (f"<filter class='categorical' column={A(fn)}><groupfilter function='member' level='[none:Calculation_2002:nk]' "
                    "member='true' user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' /></filter>")
        param_ds = "<datasource name='Parameters' />"
        param_dep = (f"<datasource-dependencies datasource='Parameters'>{PARAM_XML}</datasource-dependencies>")
    if not_cleared_only:
        fr = use("Result", "none")
        filters += (f"<filter class='categorical' column={A(fr)}><groupfilter function='member' level='[none:Result:nk]' "
                    "member='&quot;Not Cleared&quot;' user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' /></filter>")
    r = [use(*x) for x in rows]
    c = [use(*x) for x in cols_]
    enc = []
    if color: enc.append(f"<color column={A(use(*color))} />")
    for d in detail: enc.append(f"<lod column={A(use(*d))} />")
    if text: enc.append(f"<text column={A(use(*text))} />")
    sorts = ""
    if sort:
        dim, meas, direction = sort
        sorts = (f"<shelf-sorts><shelf-sort-v2 dimension-to-sort={A(use(*dim))} direction={A(direction)} is-on-innermost-dimension='true' "
                 f"measure-to-sort-by={A(use(*meas))} shelf='rows' /></shelf-sorts>")
    lab = ("<style><style-rule element='mark'><format attr='mark-labels-show' value='true' />"
           "<format attr='mark-labels-cull' value='true' /></style-rule></style>") if label else ""
    custom = ""
    tstyle = "<style />"
    if axis:
        rules = []
        for (f, how), shelf, lo, hi in axis:
            rules.append(f"<encoding attr='space' class='0' field={A(use(f, how))} field-type='quantitative' max='{hi}' min='{lo}' range-type='fixed' scope={A(shelf)} type='space' />")
        tstyle = "<style><style-rule element='axis'>" + "".join(rules) + "</style-rule></style>"
    if kpi_caption:
        custom = (f"<customized-label><formatted-text><run fontsize='10'>{escape(kpi_caption)}</run><run>&#10;</run>"
                  f"<run bold='true' fontsize='20'><![CDATA[<{use(*text)}>]]></run></formatted-text></customized-label>")
        tstyle = ("<style><style-rule element='cell'><format attr='text-align' value='center' />"
                  "<format attr='vertical-align' value='center' /></style-rule></style>")
    title_xml = (f"<layout-options><title><formatted-text><run bold='true' fontsize='12'>{escape(title)}</run></formatted-text></title></layout-options>"
                 if title else "<layout-options><title><formatted-text><run> </run></formatted-text></title></layout-options>")
    return f"""
    <worksheet name={A(name)}>
      {title_xml}
      <table>
        <view>
          <datasources><datasource caption={A(CAP)} name={A(DS)} />{param_ds}</datasources>
          <datasource-dependencies datasource={A(DS)}>{''.join(deps)}</datasource-dependencies>
          {param_dep}
          {filters}
          {sorts}
          <aggregation value='true' />
        </view>
        {tstyle}
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class={A(mark)} />
            <encodings>{''.join(enc)}</encodings>
            {custom}
            {lab}
          </pane>
        </panes>
        {'<rows>' + ' / '.join(r) + '</rows>' if r else '<rows />'}
        {'<cols>' + ' / '.join(c) + '</cols>' if c else '<cols />'}
      </table>
      <simple-id uuid={A(U())} />
    </worksheet>"""


# ------------------------------------------------------------------ insights for titles
w = df.assign(w=df["Grade Point"] * df["Credits"])
sg = w.groupby("Student").apply(lambda g: g.w.sum() / g.Credits.sum())
sub = df.groupby("Subject")["Grade Point"].mean().sort_values()
clr = df.groupby("Subject")["Result"].apply(lambda s: (s == "Cleared").mean()).sort_values()
typ = w.groupby("Course Type").apply(lambda g: g.w.sum() / g.Credits.sum())
gcount = df["Grade"].value_counts()
labels = sorted(df["Student"].unique())
DEFAULT_STUDENT = labels[0]
PARAM_XML = (f"<column caption='Select Student' datatype='string' name={A(PARAM_COL)} param-domain-type='list' role='measure' "
             f"type='nominal' value={A(chr(34) + DEFAULT_STUDENT + chr(34))}><calculation class='tableau' formula={A(chr(34) + DEFAULT_STUDENT + chr(34))} />"
             "<members>" + "".join(f"<member value={A(chr(34) + l + chr(34))} />" for l in labels) + "</members></column>")

S = []
S.append(sheet("KPI Students", None, mark="Text", text=("Student", "ctd"), kpi_caption="Students"))
S.append(sheet("KPI Cleared", None, mark="Text", text=("Calculation_1001", "avg"), kpi_caption="Papers cleared"))
S.append(sheet("KPI SGPA", None, mark="Text", text=("Calculation_1003", "usr"), kpi_caption="Class SGPA"))
S.append(sheet("KPI Backlog", None, mark="Text", text=("Calculation_1007", "usr"), kpi_caption="Students with a backlog"))
S.append(sheet("Grade Distribution", f"A is the most common grade ({gcount.get('A', 0)} of {len(df)} results); {gcount.get('O', 0)} O grades",
               cols_=[("Grade", "none")], rows=[("__records__", None)], mark="Bar", color=("Grade", "none"), text=("__records__", None)))
S.append(sheet("SGPA Bands", f"{(sg >= 8).sum()} of {len(sg)} students have SGPA 8 or above; {(sg < 6).sum()} are below 6",
               cols_=[("Calculation_2005", "none")], rows=[("Student", "ctd")], mark="Bar", color=("Calculation_2005", "none"),
               text=("Student", "ctd")))
S.append(sheet("Subject Difficulty", f"{sub.index[0]} is the toughest subject (avg grade point {sub.iloc[0]:.2f}); {sub.index[-1]} the best ({sub.iloc[-1]:.2f})",
               rows=[("Subject", "none")], cols_=[("Grade Point", "avg")], mark="Bar", color=("Grade Point", "avg"),
               text=("Grade Point", "avg"), sort=(("Subject", "none"), ("Grade Point", "avg"), "ASC"),
               axis=[(("Grade Point", "avg"), "cols", 0, 10)]))
S.append(sheet("Grade Mix by Subject", "How the grades are spread in each subject",
               rows=[("Subject", "none")], cols_=[("__records__", None)], mark="Bar", color=("Grade", "none"), text=("__records__", None)))
S.append(sheet("Clearance by Subject", f"Clearance rate is lowest in {clr.index[0]} ({clr.iloc[0]:.1%})",
               rows=[("Subject", "none")], cols_=[("Calculation_1001", "avg")], mark="Bar", color=("Calculation_1001", "avg"),
               text=("Calculation_1001", "avg"), sort=(("Subject", "none"), ("Calculation_1001", "avg"), "ASC")))
S.append(sheet("Course Type", "Average grade point: theory + practical vs theory + practical + project",
               cols_=[("Course Type", "none")], rows=[("Calculation_1003", "usr")], mark="Bar", color=("Course Type", "none"),
               text=("Calculation_1003", "usr"), axis=[(("Calculation_1003", "usr"), "rows", 0, 10)]))
S.append(sheet("Top Performers", f"Top SGPA in the class: {sg.max():.2f} (students are anonymised codes)",
               rows=[("Student", "none")], cols_=[("Calculation_1003", "usr")], mark="Bar", color=("Calculation_1003", "usr"),
               text=("Calculation_1003", "usr"), sort=(("Student", "none"), ("Calculation_1003", "usr"), "DESC"),
               axis=[(("Calculation_1003", "usr"), "cols", 0, 10)]))
S.append(sheet("Backlogs by Subject", "Results that were not cleared (F, S, M, R) in each subject",
               rows=[("Subject", "none")], cols_=[("Calculation_1007", "usr")], mark="Bar", color=("Subject", "none"),
               text=("Calculation_1007", "usr"), sort=(("Subject", "none"), ("Calculation_1007", "usr"), "DESC")))
S.append(sheet("Profile Grades", "Grade point in every subject (colour = grade)",
               rows=[("Subject", "none")], cols_=[("Grade Point", "avg")], mark="Bar", color=("Grade", "none"),
               text=("Grade", "none"), selected_only=True, axis=[(("Grade Point", "avg"), "cols", 0, 10)]))
S.append(sheet("Profile Details", "Selected student",
               rows=[("Student", "none"), ("Batch", "none")], mark="Text", text=("Calculation_1003", "usr"), selected_only=True))
S.append(sheet("Profile Credits", "Credits and grades of the selected student",
               rows=[("Subject", "none"), ("Credit Split", "none"), ("Grade Label", "none")], mark="Text", text=("Credits", "sum"),
               selected_only=True))

bl = df[df.Result == "Not Cleared"].groupby("Student").size()
hard = df.groupby(["Subject", "Grade"]).size()
mn = df.groupby("Student")["Grade Point"].min()
S.append(sheet("Grade Count Table", "Grade count for every subject and grade (darker = more students)",
               rows=[("Subject", "none")], cols_=[("Grade", "none")], mark="Square", color=("__records__", None), text=("__records__", None)))
S.append(sheet("Credits vs Performance", "Do subjects with more credits get lower grades?",
               cols_=[("Credits", "avg")], rows=[("Grade Point", "avg")], mark="Circle", color=("Subject", "none"),
               text=("Subject", "none"), axis=[(("Grade Point", "avg"), "rows", 6, 9), (("Credits", "avg"), "cols", 0, 7)]))
S.append(sheet("Backlogs per Student", f"{len(bl)} students have backlogs: {(bl == 1).sum()} have one, {(bl >= 2).sum()} have two or more",
               cols_=[("Calculation_2006", "none")], rows=[("Student", "ctd")], mark="Bar", color=("Calculation_2006", "none"),
               text=("Student", "ctd")))
S.append(sheet("Backlog Students", "Every result that was not cleared (student code, subject, grade)",
               rows=[("Student", "none"), ("Subject", "none")], mark="Text", text=("Grade", "none"), not_cleared_only=True))
S.append(sheet("Consistency", f"Weakest subject vs SGPA (each dot = one student); {(mn >= 8).sum()} students scored A or better in every subject",
               cols_=[("Calculation_1003", "usr")], rows=[("Grade Point", "min")], mark="Circle", color=("Calculation_1003", "usr"),
               detail=[("Student", "none")], label=False,
               axis=[(("Calculation_1003", "usr"), "cols", 0, 10), (("Grade Point", "min"), "rows", 0, 10)]))

# ------------------------------------------------------------------ dashboards
def zone_sheet(i, name, x, y, w, h):
    return (f"<zone h='{h}' id='{i}' name={A(name)} w='{w}' x='{x}' y='{y}'><zone-style>"
            "<format attr='border-color' value='#d9d9d9' /><format attr='border-style' value='solid' />"
            "<format attr='border-width' value='1' /><format attr='margin' value='4' /></zone-style></zone>")


def dashboard(name, title, grid, param=False):
    zones, i, y = [], 10, 7000
    if param:
        zones.append(f"<zone h='6000' id='9' mode='compact' param='[Parameters].{PARAM_COL}' type-v2='paramctrl' w='40000' x='500' y='7000' />")
        y = 13000
    for h, names in grid:
        x, w = 500, 99000 // len(names)
        for n in names:
            zones.append(zone_sheet(i, n, x, y, w, h)); i += 1; x += w
        y += h
    return f"""
    <dashboard enable-sort-zone-taborder='true' name={A(name)}>
      <layout-options><title><formatted-text><run bold='true' fontalignment='1' fontsize='16'>{escape(title)}</run></formatted-text></title></layout-options>
      <style />
      <size sizing-mode='automatic' />
      <zones>
        <zone h='100000' id='4' type-v2='layout-basic' w='100000' x='0' y='0'>
          <zone fixed-size='60' h='6500' id='5' is-fixed='true' type-v2='title' w='99000' x='500' y='500' />
          {''.join(zones)}
        </zone>
      </zones>
      <simple-id uuid={A(U())} />
    </dashboard>""", [n for _, ns in grid for n in ns]


DASH = [
    dashboard("Overview", "MCA 2025-27 Batch - Semester 2 Results: Overview (CUTM)",
              [(14000, ["KPI Students", "KPI Cleared", "KPI SGPA", "KPI Backlog"]), (78000, ["Grade Distribution", "SGPA Bands"])]),
    dashboard("Subject Analysis", "MCA 2025-27 Semester 2 - Subject-wise Performance",
              [(46000, ["Subject Difficulty", "Clearance by Subject"]), (46000, ["Grade Mix by Subject", "Backlogs by Subject"])]),
    dashboard("SGPA Analysis", "MCA 2025-27 Semester 2 - SGPA and Top Performers",
              [(92000, ["Top Performers", "Course Type"])]),
    dashboard("Student Profile", "MCA 2025-27 Semester 2 - Student Report Card (choose a student above)",
              [(14000, ["Profile Details"]), (39000, ["Profile Grades"]), (39000, ["Profile Credits"])], param=True),
]
DASH += [
    dashboard("Grade Heatmap", "MCA 2025-27 Semester 2 - Grade Heatmap and Credits",
              [(60000, ["Grade Count Table"]), (32000, ["Credits vs Performance"])]),
    dashboard("Backlog Analysis", "MCA 2025-27 Semester 2 - Backlog Analysis (papers not cleared)",
              [(46000, ["Backlogs per Student", "Backlogs by Subject"]), (46000, ["Backlog Students"])]),
    dashboard("Consistency Analysis", "MCA 2025-27 Semester 2 - How Consistent Are Students Across Subjects?",
              [(92000, ["Consistency", "SGPA Bands"])]),
]
DNAMES = ["Overview", "Subject Analysis", "SGPA Analysis", "Student Profile", "Grade Heatmap", "Backlog Analysis", "Consistency Analysis"]

# ------------------------------------------------------------------ datasource
colxml = "".join(f"<column datatype={A(t)} name={A(c)} ordinal='{i}' />" for i, (c, t) in enumerate(cols))
relation = (f"<relation connection={A(TS)} name='mca_2025_sem2_results.csv' table='[mca_2025_sem2_results#csv]' type='table'>"
            f"<columns character-set='UTF-8' header='yes' locale='en_IN' separator=','>{colxml}</columns></relation>")
meta = ["<metadata-record class='capability'><remote-name /><remote-type>0</remote-type><parent-name>[mca_2025_sem2_results.csv]</parent-name>"
        "<remote-alias /><aggregation>Count</aggregation><contains-null>true</contains-null><attributes>"
        "<attribute datatype='string' name='character-set'>&quot;UTF-8&quot;</attribute>"
        "<attribute datatype='string' name='collation'>&quot;en_GB&quot;</attribute>"
        "<attribute datatype='string' name='field-delimiter'>&quot;,&quot;</attribute>"
        "<attribute datatype='string' name='header-row'>&quot;true&quot;</attribute>"
        "<attribute datatype='string' name='locale'>&quot;en_IN&quot;</attribute>"
        "<attribute datatype='string' name='single-char'>&quot;&quot;</attribute></attributes></metadata-record>"]
for i, (c, t) in enumerate(cols):
    meta.append(f"<metadata-record class='column'><remote-name>{escape(c)}</remote-name><remote-type>{REMOTE[t]}</remote-type>"
                f"<local-name>{escape('[' + c + ']')}</local-name><parent-name>[mca_2025_sem2_results.csv]</parent-name>"
                f"<remote-alias>{escape(c)}</remote-alias><ordinal>{i}</ordinal><local-type>{t}</local-type>"
                f"<aggregation>{AGG[t]}</aggregation><contains-null>true</contains-null>"
                f"<object-id>[{OBJ}]</object-id></metadata-record>")
grade_sort = "".join(f"<bucket>&quot;{g}&quot;</bucket>" for g in ["O", "E", "A", "B", "C", "D", "F", "S", "M", "R"])
band_sort = "".join(f"<bucket>&quot;{g}&quot;</bucket>" for g in ["Below 6", "6 - 7", "7 - 8", "8 - 9", "9 - 10"])
datasource = f"""
    <datasource caption={A(CAP)} inline='true' name={A(DS)} version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption={A(CAP)} name={A(TS)}>
            <connection class='textscan' directory='Data/Datasets' filename='mca_2025_sem2_results.csv' password='' server='' />
          </named-connection>
        </named-connections>
        {relation}
        <metadata-records>{''.join(meta)}</metadata-records>
      </connection>
      <aliases enabled='yes' />
      {''.join(col_def(k) for k in CALCS)}
      {col_def('Semester')}
      {col_def('Credits')}
      {col_def('Grade Point')}
      <column datatype='string' name='[Student]' role='dimension' type='nominal' />
      <column caption='Results' datatype='table' name={A('[__tableau_internal_object_id__].[' + OBJ + ']')} role='measure' type='quantitative' />
      <column-instance column='[Grade]' derivation='None' name='[none:Grade:nk]' pivot='key' type='nominal' />
      <column-instance column='[Calculation_2005]' derivation='None' name='[none:Calculation_2005:nk]' pivot='key' type='nominal' />
      <layout dim-ordering='alphabetic' measure-ordering='alphabetic' show-structure='true' />
      <style>
        <style-rule element='mark'>
          <encoding attr='color' field='[none:Grade:nk]' type='palette'>
            <map to='#1a7f37'><bucket>&quot;O&quot;</bucket></map><map to='#4c9f38'><bucket>&quot;E&quot;</bucket></map>
            <map to='#8cc34a'><bucket>&quot;A&quot;</bucket></map><map to='#f2c12e'><bucket>&quot;B&quot;</bucket></map>
            <map to='#f29d38'><bucket>&quot;C&quot;</bucket></map><map to='#e8692c'><bucket>&quot;D&quot;</bucket></map>
            <map to='#c62828'><bucket>&quot;F&quot;</bucket></map>
            <map to='#8e24aa'><bucket>&quot;S&quot;</bucket></map><map to='#6d4c41'><bucket>&quot;M&quot;</bucket></map>
            <map to='#546e7a'><bucket>&quot;R&quot;</bucket></map>
          </encoding>
          <encoding attr='color' field='[none:Calculation_2005:nk]' type='palette'>
            <map to='#c62828'><bucket>&quot;Below 6&quot;</bucket></map><map to='#f29d38'><bucket>&quot;6 - 7&quot;</bucket></map>
            <map to='#f2c12e'><bucket>&quot;7 - 8&quot;</bucket></map><map to='#8cc34a'><bucket>&quot;8 - 9&quot;</bucket></map>
            <map to='#1a7f37'><bucket>&quot;9 - 10&quot;</bucket></map>
          </encoding>
        </style-rule>
      </style>
      <default-sorts>
        <manual-sort column='[none:Grade:nk]' direction='ASC'><dictionary>{grade_sort}</dictionary></manual-sort>
        <manual-sort column='[none:Calculation_2005:nk]' direction='ASC'><dictionary>{band_sort}</dictionary></manual-sort>
      </default-sorts>
      <object-graph>
        <objects>
          <object caption='mca_2025_sem2_results.csv' id={A(OBJ)}>
            <properties context=''>{relation}</properties>
          </object>
        </objects>
      </object-graph>
    </datasource>"""


def win_ws(n):
    return (f"<window class='worksheet' name={A(n)}><cards><edge name='left'><strip size='160'><card type='pages' />"
            "<card type='filters' /><card type='marks' /></strip></edge><edge name='top'><strip size='2147483647'>"
            "<card type='columns' /></strip><strip size='2147483647'><card type='rows' /></strip>"
            "<strip size='2147483647'><card type='title' /></strip></edge></cards>"
            f"<simple-id uuid={A(U())} /></window>")


def win_db(n, sheets, active=False):
    vps = "".join(f"<viewpoint name={A(s)}><zoom type='entire-view' /></viewpoint>" for s in sorted(set(sheets)))
    return (f"<window class='dashboard'{' maximized=\"true\"' if active else ''} name={A(n)}><viewpoints>{vps}</viewpoints>"
            f"<active id='-1' /><simple-id uuid={A(U())} /></window>")


names = [s.split("name=")[1].split(">")[0].strip("'\"") for s in S]
xml = f"""<?xml version='1.0' encoding='utf-8' ?>

<!-- build 20262.26.0603.1643                               -->
<workbook original-version='18.1' source-build='2026.2.0 (20262.26.0603.1643)' source-platform='win' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <document-format-change-manifest>
    <AccessibleZoneTabOrder /><AnimationOnByDefault /><AutoCreateAndUpdateDSDPhoneLayouts /><IntuitiveSorting /><IntuitiveSorting_SP2 />
    <MapboxVectorStylesAndLayers /><MarkAnimation /><ObjectModelEncapsulateLegacy /><ObjectModelTableType /><SchemaViewerObjectModel />
    <SetMembershipControl /><SheetIdentifierTracking /><SortTagCleanup /><WindowsPersistSimpleIdentifiers />
  </document-format-change-manifest>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>
  <datasources>
    <datasource hasconnection='false' inline='true' name='Parameters' version='18.1'>
      <aliases enabled='yes' />
      {PARAM_XML}
    </datasource>{datasource}
  </datasources>
  <worksheets>{''.join(S)}
  </worksheets>
  <dashboards>{''.join(d for d, _ in DASH)}
  </dashboards>
  <windows source-height='37'>
    {''.join(win_ws(n) for n in names)}
    {''.join(win_db(n, sh, active=(k == 0)) for k, (n, (_, sh)) in enumerate(zip(DNAMES, DASH)))}
  </windows>
</workbook>
"""
os.makedirs("out", exist_ok=True)
twb = "MCA 2025 Semester 2 Result Analysis.twb"
open(os.path.join("out", twb), "w", encoding="utf-8").write(xml)
with zipfile.ZipFile("out/MCA_2025_Sem2_Result_Analysis.twbx", "w", zipfile.ZIP_DEFLATED) as z:
    z.write(os.path.join("out", twb), twb)
    z.write(CSV, "Data/Datasets/mca_2025_sem2_results.csv")
print("sheets:", names)
print("dashboards", DNAMES)
