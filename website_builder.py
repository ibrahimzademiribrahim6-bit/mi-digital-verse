import os
import re
from dotenv import load_dotenv
from crewai import LLM, Agent, Task, Crew, Process
from crewai_tools import SerperDevTool

load_dotenv()

llm = LLM(
    model="deepseek/deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY")
)

search_tool = SerperDevTool()

# instructions.txt oxu (əgər varsa)
instructions = ""
if os.path.exists("instructions.txt"):
    with open("instructions.txt", "r", encoding="utf-8") as f:
        instructions = f.read()

researcher = Agent(
    role="Araşdırmaçı",
    goal="Anime, manhwa və icma ilə bağlı ən son xəbərləri tap.",
    backstory="Sən internetdə sürətlə axtarış edən təcrübəli tədqiqatçısan.",
    tools=[search_tool],
    llm=llm,
    verbose=True
)

designer = Agent(
    role="Veb Dizayner",
    goal="Araşdırma nəticələrinə əsaslanaraq müasir, təhlükəsiz HTML səhifələri yarat.",
    backstory="Sən cyber/neon estetikada mütəxəssis, Tailwind CSS ilə təmiz kod yazan peşəkar frontendçisən.",
    llm=llm,
    verbose=True
)

critic = Agent(
    role="Təhlükəsizlik Mütəxəssisi",
    goal="Yaradılan kodu yoxla, səhv varsa düzəlt.",
    backstory="Sən kodu yoxlayan, təhlükəsizlik problemlərini tapan tənqidçisən.",
    llm=llm,
    verbose=True
)

research_task = Task(
    description="Anime, manhwa ilə bağlı son 5 vacib xəbəri tap. Hər biri üçün qısa xülasə yaz.",
    agent=researcher,
    expected_output="Xəbər başlıqları və qısa xülasələr."
)

design_task = Task(
    description=f"""
    Aşağıdakı tələblərə uyğun 4 HTML faylı yarat:
    {instructions}
    - index.html, news.html, manhwa.html, community.html
    - Ümumi dizayn: Tailwind CSS, cyber/neon tema, dark/light rejimi, navbar (Home, News, Manhwa Hub, Community).
    - Hər səhifədə footer, modal qeydiyyat forması.
    - Xəbərlər səhifəsində araşdırma nəticələrini istifadə et.
    - Təhlükəsizlik: formada heç bir xarici skript olmasın, bütün linklər rel='noopener'.
    Çıxış formatı əvvəlcə bu olmalıdır:
    === index.html ===
    (HTML kodu)
    === news.html ===
    (HTML kodu)
    === manhwa.html ===
    (HTML kodu)
    === community.html ===
    (HTML kodu)
    """,
    agent=designer,
    expected_output="Ayrı-ayrı HTML kodları markerlərlə."
)

critic_task = Task(
    description="""
    Dizaynerin yaratdığı HTML kodunu yoxla. Problemlər varsa, onları sadəcə qeyd et.
    """,
    agent=critic,
    expected_output="Tənqidi rəy."
)

crew = Crew(
    agents=[researcher, designer, critic],
    tasks=[research_task, design_task, critic_task],
    process=Process.sequential,
    verbose=True
)

# İşə salırıq
crew.kickoff()

# Dizaynerin çıxardığı nəticəni ayrıca götür
raw_design = ""
try:
    raw_design = str(design_task.output)  # dizaynerin tapşırıq çıxışı
except Exception:
    pass

if not raw_design or raw_design == "None":
    # Bəzən output task atributunda olmur, yoxlayırıq
    try:
        raw_design = str(designer.get_last_output())
    except Exception:
        raw_design = ""

# Nəticəni fayla yaz (həmişə görmək üçün)
with open("raw_design.txt", "w", encoding="utf-8") as f:
    f.write(raw_design)

# HTML fayllarını çıxar
os.makedirs("output", exist_ok=True)
pattern = r'===\s*([\w.-]+)\s*===\s*(.*?)(?=\n===|\Z)'
matches = re.findall(pattern, raw_design, re.DOTALL)

if matches:
    for filename, html in matches:
        html = html.strip()
        if html:
            with open(f"output/{filename}", "w", encoding="utf-8") as f:
                f.write(html)
    print(f"✅ {len(matches)} fayl markerlərlə yaradıldı.")
else:
    html_blocks = re.findall(r'<html.*?</html>', raw_design, re.DOTALL | re.IGNORECASE)
    if html_blocks:
        filenames = ["index.html", "news.html", "manhwa.html", "community.html"]
        for i, block in enumerate(html_blocks[:4]):
            filename = filenames[i] if i < len(filenames) else f"page{i+1}.html"
            with open(f"output/{filename}", "w", encoding="utf-8") as f:
                f.write(block.strip())
        print(f"✅ {len(html_blocks[:4])} fayl HTML bloklarından yaradıldı.")
    else:
        print("❌ Hələ də HTML tapılmadı.")
        print("raw_design.txt faylını aç və mənə ilk 20 sətirini göndər.")