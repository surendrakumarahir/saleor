"""Seed 10 comprehensive academic blog posts for EasyToPick."""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from saleor.blog.models import (
    BlogAuthor,
    BlogCategory,
    BlogPost,
    BlogPostStatus,
    BlogTag,
)


class Command(BaseCommand):
    help = "Seed 10 production-grade educational blogs for EasyToPick bookstore."

    def handle(self, *args, **options):
        self.stdout.write("Seeding categories...")

        categories_data = [
            {
                "name": "NEET & JEE",
                "slug": "neet-jee",
                "description": "Targeted strategies and top recommended books for medical and engineering entrance exams.",
                "badge_color": "bg-amber-100 text-amber-900 border-amber-300",
                "seo_title": "NEET & JEE Entrance Exam Preparation Guides & Recommended Books | EasyToPick",
                "seo_description": "Comprehensive guides, book recommendations and study strategies for NEET and JEE aspirants by Kota faculty.",
            },
            {
                "name": "Govt Exams",
                "slug": "govt-exams",
                "description": "Rajasthan & National competitive exam guides: RAS, REET, Police, Patwari, CET, SSC.",
                "badge_color": "bg-blue-100 text-blue-900 border-blue-300",
                "seo_title": "Rajasthan & National Govt Competitive Exam Guides & Books | EasyToPick",
                "seo_description": "Top booklists, syllabus breakdowns and preparation strategies for Rajasthan Govt exams, RAS, REET and CET.",
            },
            {
                "name": "Study Strategies",
                "slug": "study-strategies",
                "description": "Proven revision frameworks, active recall methods, and time management hacks.",
                "badge_color": "bg-emerald-100 text-emerald-900 border-emerald-300",
                "seo_title": "Proven Academic Study Strategies & Revision Frameworks | EasyToPick",
                "seo_description": "Boost your retention with topper-tested study techniques, active recall frameworks and daily study timetables.",
            },
            {
                "name": "Book Reviews",
                "slug": "book-reviews",
                "description": "In-depth reviews and comparisons of standard reference textbooks and notes.",
                "badge_color": "bg-orange-100 text-orange-900 border-orange-300",
                "seo_title": "Honest Book Reviews & Reference Textbook Comparisons | EasyToPick",
                "seo_description": "Unbiased, detailed comparisons of competitive exam books, NCERT guides, modules and problem practice sets.",
            },
            {
                "name": "Kota Student Life",
                "slug": "kota-student-life",
                "description": "Hostel survival guides, daily study routines, and student wellness advice.",
                "badge_color": "bg-purple-100 text-purple-900 border-purple-300",
                "seo_title": "Kota Coaching & Student Life Guides | EasyToPick",
                "seo_description": "Advice on Kota coaching routines, hostel living, test series stress management and staying motivated.",
            },
        ]

        cats = {}
        for c in categories_data:
            cat, _ = BlogCategory.objects.update_or_create(
                slug=c["slug"],
                defaults={
                    "name": c["name"],
                    "description": c["description"],
                    "badge_color": c["badge_color"],
                    "seo_title": c["seo_title"],
                    "seo_description": c["seo_description"],
                    "is_active": True,
                },
            )
            cats[c["slug"]] = cat

        self.stdout.write("Seeding authors...")
        authors_data = [
            {
                "display_name": "Dr. Rajesh Sharma",
                "slug": "dr-rajesh-sharma",
                "designation": "Senior Academic Mentor & Ex-Kota Faculty",
                "bio": "Over 14 years of teaching physics to medical aspirants in Kota. Guided 150+ students into top AIIMS & government medical colleges.",
                "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80",
                "social_links": {"twitter": "https://twitter.com", "linkedin": "https://linkedin.com"},
            },
            {
                "display_name": "Priya Rathore",
                "slug": "priya-rathore",
                "designation": "REET & RAS Exam Analyst",
                "bio": "Qualified RAS Mains and educational researcher specializing in Rajasthan board curricula and competitive examinations.",
                "avatar": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=200&q=80",
                "social_links": {"twitter": "https://twitter.com"},
            },
            {
                "display_name": "Er. Vikramaditya Verma",
                "slug": "er-vikramaditya-verma",
                "designation": "IIT-JEE Mathematics Coach & Author",
                "bio": "IIT Bombay alumnus with 11 years coaching experience in Kota and Jaipur. Author of competitive algebra and calculus problem sets.",
                "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=200&q=80",
                "social_links": {"linkedin": "https://linkedin.com"},
            },
            {
                "display_name": "Amitabh Meena",
                "slug": "amitabh-meena",
                "designation": "Chemistry Faculty & Kota Hostel Counselor",
                "bio": "Specialist in Organic and Physical Chemistry with 8 years in landmark Kota institutions. Passionate about student mental wellness.",
                "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=200&q=80",
                "social_links": {"twitter": "https://twitter.com"},
            },
        ]

        authors = {}
        for a in authors_data:
            auth, _ = BlogAuthor.objects.update_or_create(
                slug=a["slug"],
                defaults={
                    "display_name": a["display_name"],
                    "designation": a["designation"],
                    "bio": a["bio"],
                    "avatar": a["avatar"],
                    "social_links": a["social_links"],
                },
            )
            authors[a["slug"]] = auth

        self.stdout.write("Seeding tags...")
        tag_names = [
            "NEET 2026", "Physics", "IIT-JEE", "Chemistry", "Biology", "NCERT Books",
            "Kota Mentors", "Study Routine", "Rajasthan Govt", "RAS 2026", "CET Exam",
            "Book Review", "Allen Modules", "Mathematics", "Hostel Life", "CBSE Boards"
        ]
        tags = {}
        for tn in tag_names:
            tslug = slugify(tn)
            tag, _ = BlogTag.objects.update_or_create(slug=tslug, defaults={"name": tn})
            tags[tslug] = tag

        self.stdout.write("Seeding 10 production blogs...")
        posts_data = [
            {
                "slug": "neet-2026-recommended-books-physics-strategy-kota",
                "title": "Complete Guide to NEET 2026: Recommended Books & Physics Strategy by Kota Mentors",
                "excerpt": "Struggling with Physics in NEET? Kota mentors break down chapter-wise weightage, essential NCERT touchpoints, and the exact reference books you need to cross 160+ in Physics.",
                "featured_image": "https://images.unsplash.com/photo-1532012164546-f432f2e3dd45?auto=format&fit=crop&w=1200&q=80",
                "featured_image_alt": "NEET preparation books and notes on a wooden desk",
                "primary_category": cats["neet-jee"],
                "author": authors["dr-rajesh-sharma"],
                "is_featured": True,
                "reading_time_minutes": 7,
                "tags": [tags["neet-2026"], tags["physics"], tags["kota-mentors"], tags["ncert-books"]],
                "seo_title": "NEET 2026 Physics Strategy & Recommended Books Guide | EasyToPick",
                "seo_description": "Master NEET 2026 Physics with Kota faculty recommendations. Discover chapter weightage, NCERT tips, and top practice books for scoring 160+ in physics.",
                "content_html": """
<h2>Why Physics Decides Your NEET Rank</h2>
<p>While almost all medical aspirants spend hundreds of hours memorizing Biology and inorganic chemistry, Physics consistently acts as the gatekeeper separating a 580 score from a 670+ score in NEET. A score above 160 in Physics almost guarantees admission to premier government medical colleges.</p>
<h3>Core Booklist Recommended by Kota Faculties</h3>
<p>Here is the disciplined hierarchy of resources you should follow in sequence:</p>
<ul>
    <li><strong>NCERT Physics (Class 11 & 12):</strong> Do not skip the "Points to Ponder", solved examples, and back-of-chapter exercises.</li>
    <li><strong>DC Pandey Objective Physics for Medical Entrances:</strong> Ideal for building problem-solving intuition from fundamentals to high-difficulty numericals.</li>
    <li><strong>Errorless Physics (Universal Self Scorer):</strong> Unmatched volume of chapter-wise previous years' questions categorized by sub-topics.</li>
</ul>
<h3>High-Yield Chapters in Physics</h3>
<p>Analyze previous 5 years' NEET question papers, and you will notice nearly 60% of questions originate from just 5 core clusters: Modern Physics, Optics, Current Electricity & Magnetism, Thermodynamics, and Mechanics.</p>
<blockquote>"Never attempt reference book problems before you have derived every single formula on a blank sheet of paper from first principles." — Dr. Rajesh Sharma</blockquote>
""",
                "table_of_contents": [
                    {"id": "why-physics-decides-neet-rank", "title": "Why Physics Decides Your NEET Rank", "level": 2},
                    {"id": "core-booklist-recommended-by-kota-faculties", "title": "Core Booklist Recommended by Kota Faculties", "level": 2},
                    {"id": "high-yield-chapters-in-physics", "title": "High-Yield Chapters in Physics", "level": 2},
                ],
                "recommended_books": [
                    {
                        "title": "DC Pandey Objective Physics for NEET (Vol 1 & 2)",
                        "subtitle": "Arihant Publications • Latest Edition",
                        "price": "₹1,240",
                        "originalPrice": "₹1,650",
                        "discountBadge": "25% OFF",
                        "href": "/products/dc-pandey-physics-neet",
                        "image": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=400&q=80",
                        "badge": "Top Seller",
                    }
                ],
            },
            {
                "slug": "3-pass-ncert-revision-technique-biology-chemistry",
                "title": "The 3-Pass NCERT Revision Technique: How Kota Toppers Memorize Biology & Chemistry",
                "excerpt": "Passive reading leads to dangerous illusion of competence. Learn the scientifically backed 3-Pass system used by AIIMS rankers to achieve 350+ in Biology.",
                "featured_image": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?auto=format&fit=crop&w=1200&q=80",
                "featured_image_alt": "Open NCERT textbook with highlighters and summary notes",
                "primary_category": cats["study-strategies"],
                "author": authors["amitabh-meena"],
                "is_featured": False,
                "reading_time_minutes": 6,
                "tags": [tags["ncert-books"], tags["biology"], tags["chemistry"], tags["study-routine"]],
                "seo_title": "3-Pass NCERT Revision Technique for NEET Toppers | EasyToPick",
                "seo_description": "Learn the 3-pass NCERT method for NEET Biology and Chemistry. Retain factual details and score 350+ with active recall strategies.",
                "content_html": """
<h2>The Illusion of Competence in Passive Reading</h2>
<p>Highlighting lines in your textbook feels productive, but cognitive science shows it creates a false sense of familiarity. In the examination hall, two tricky options will immediately confuse you if you haven't forced your brain into retrieval practice.</p>
<h3>Pass 1: Diagnostic Reading & Margin Annotation</h3>
<p>Read the chapter swiftly without highlighting. Understand the conceptual arc and write 3-word summaries on the page margins for every paragraph.</p>
<h3>Pass 2: Active Recall Flashcards & Diagram Cloze</h3>
<p>Cover paragraph text with a blank sheet. Try to reconstruct the details from memory. Practice redrawing NCERT diagrams without looking at labels.</p>
<h3>Pass 3: Reverse Error-Log Integration</h3>
<p>After solving 100 chapter questions, highlight only the exact NCERT lines you got wrong during mock tests. Your textbook becomes a personalized heat-map of your weak spots.</p>
""",
                "table_of_contents": [
                    {"id": "illusion-of-competence", "title": "The Illusion of Competence", "level": 2},
                    {"id": "pass-1-diagnostic", "title": "Pass 1: Diagnostic Reading", "level": 2},
                    {"id": "pass-2-active-recall", "title": "Pass 2: Active Recall & Flashcards", "level": 2},
                    {"id": "pass-3-reverse-log", "title": "Pass 3: Reverse Error-Log Integration", "level": 2},
                ],
                "recommended_books": [
                    {
                        "title": "NCERT Biology Class 11 & 12 (Original Edition)",
                        "subtitle": "NCERT Official Publication",
                        "price": "₹450",
                        "originalPrice": "₹520",
                        "discountBadge": "15% OFF",
                        "href": "/products/ncert-biology-combo",
                        "image": "https://images.unsplash.com/photo-1589829085413-56de8ae18c73?auto=format&fit=crop&w=400&q=80",
                        "badge": "Essential",
                    }
                ],
            },
            {
                "slug": "rajasthan-ras-cet-2026-best-books-history-geography",
                "title": "Rajasthan RAS & CET 2026: Best Books for Rajasthan History, Geography & Art Culture",
                "excerpt": "A definitive, syllabus-mapped book list for Rajasthan competitive exams. Clear insights on Lakshya vs Panorama vs RBSE Hindi Granth Academy.",
                "featured_image": "https://images.unsplash.com/photo-1599661046289-e31897846e41?auto=format&fit=crop&w=1200&q=80",
                "featured_image_alt": "Fort of Rajasthan symbolizing state civil services",
                "primary_category": cats["govt-exams"],
                "author": authors["priya-rathore"],
                "is_featured": False,
                "reading_time_minutes": 8,
                "tags": [tags["rajasthan-govt"], tags["ras-2026"], tags["cet-exam"], tags["book-review"]],
                "seo_title": "Rajasthan RAS & CET 2026 Booklist: History, Art & Geography | EasyToPick",
                "seo_description": "Definitive booklist for Rajasthan RAS Prelims and CET 2026. Discover the top authentic reference books for Rajasthan GK.",
                "content_html": """
<h2>The Weightage of Rajasthan GK in State Exams</h2>
<p>Whether you are appearing for RAS Prelims, Teacher Grade I/II/III, Rajasthan Police SI, or CET, more than 40-50% of the entire paper directly tests Rajasthan History, Art, Culture, Heritage, and Geography.</p>
<h3>Authentic Reference Books (Hindi Granth Academy)</h3>
<ul>
    <li><strong>Rajasthan Ka Itihas by Dr. Gopinath Sharma:</strong> The primary gold standard cited by the RPSC board for disputable answers.</li>
    <li><strong>Rajasthan Ka Bhugol by Dr. H.M. Saxena:</strong> Authentic economic and physical geography data directly accepted in objections.</li>
    <li><strong>Rajasthan Sanskritik Parampara by Jai Singh Neeraj:</strong> In-depth coverage of folklore, fairs, architectural styles, and tribal traditions.</li>
</ul>
<h3>Compilation Guidebooks for Quick Revisions</h3>
<p>For daily objective practice, Lakshay Rajasthan GK or Panorama provide excellent chapter-wise question banks and map illustrations.</p>
""",
                "table_of_contents": [
                    {"id": "weightage-of-rajasthan-gk", "title": "Weightage of Rajasthan GK", "level": 2},
                    {"id": "authentic-reference-books", "title": "Authentic Reference Books (Hindi Granth Academy)", "level": 2},
                    {"id": "compilation-guidebooks", "title": "Compilation Guidebooks for Practice", "level": 2},
                ],
                "recommended_books": [
                    {
                        "title": "Rajasthan Ka Itihas - Dr. Gopinath Sharma",
                        "subtitle": "Hindi Granth Academy Official",
                        "price": "₹380",
                        "originalPrice": "₹450",
                        "discountBadge": "15% OFF",
                        "href": "/products/rajasthan-itihas-gopinath-sharma",
                        "image": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=400&q=80",
                        "badge": "RPSC Standard",
                    }
                ],
            },
            {
                "slug": "coaching-modules-vs-standard-textbooks-comparison",
                "title": "Coaching Modules vs Standard Reference Textbooks: Which One Should You Buy?",
                "excerpt": "Should you purchase Allen/Resonance/FIITJEE study packages or stick with classic authors like HC Verma and Morrison Boyd? An honest, unbiased breakdown.",
                "featured_image": "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?auto=format&fit=crop&w=1200&q=80",
                "featured_image_alt": "Stacked coaching material and hardcover reference textbooks",
                "primary_category": cats["book-reviews"],
                "author": authors["er-vikramaditya-verma"],
                "is_featured": False,
                "reading_time_minutes": 5,
                "tags": [tags["allen-modules"], tags["book-review"], tags["iit-jee"], tags["neet-2026"]],
                "seo_title": "Coaching Modules vs Reference Books: Complete Guide | EasyToPick",
                "seo_description": "Comparing Allen, Resonance coaching modules with HC Verma and standard reference textbooks for JEE & NEET.",
                "content_html": """
<h2>The Eternal Dilemma of Self-Study Aspirants</h2>
<p>Thousands of students studying online ask whether they should order Kota coaching material or purchase standard textbooks from famous authors. Here is our direct evaluation based on learning phase:</p>
<h3>Where Coaching Modules Excel</h3>
<p>Coaching packages are curated specifically for timed examinations. They break exercises into Beginner (NCERT-based), Intermediate (Main level), and Advanced (multi-concept questions). If you want structured homework assignments, modules provide ready-made graded question banks.</p>
<h3>Where Reference Books Outperform</h3>
<p>Books like HC Verma's <em>Concepts of Physics</em> or I.E. Irodov explain underlying conceptual nuances with unmatched elegance. If a coaching module explanation feels mechanical, standard textbooks build lifelong mathematical and physical thinking.</p>
""",
                "table_of_contents": [
                    {"id": "the-dilemma", "title": "The Eternal Dilemma", "level": 2},
                    {"id": "where-modules-excel", "title": "Where Coaching Modules Excel", "level": 2},
                    {"id": "where-reference-books-excel", "title": "Where Reference Books Outperform", "level": 2},
                ],
                "recommended_books": [],
            },
            {
                "slug": "kota-hostel-life-14-hour-study-routine-survival-guide",
                "title": "Kota Hostel Life & 14-Hour Study Routine: How to Avoid Burnout and Stay Consistent",
                "excerpt": "The psychological reality of preparing in Kota. Practical daily timetable, mess food management, and overcoming plateau phases during Sunday test series.",
                "featured_image": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1200&q=80",
                "featured_image_alt": "Students studying peacefully in a library environment",
                "primary_category": cats["kota-student-life"],
                "author": authors["amitabh-meena"],
                "is_featured": False,
                "reading_time_minutes": 9,
                "tags": [tags["hostel-life"], tags["study-routine"], tags["kota-mentors"]],
                "seo_title": "Kota Hostel Life & 14-Hour Study Routine Survival Guide | EasyToPick",
                "seo_description": "Surviving and excelling in Kota coaching culture. A healthy 14-hour timetable, nutrition tips and mental wellness strategies.",
                "content_html": """
<h2>The Reality Behind the 14-Hour Myth</h2>
<p>Many fresh arrivals in Kota force themselves into unrealistic 16-hour sleep-deprived schedules during their first month, only to burn out by November. Consistency over 18 months beats heroic 3-day bursts every single time.</p>
<h3>The 3x4 Block Daily Timetable</h3>
<ul>
    <li><strong>Block 1 (Morning 7:30 AM - 11:30 AM):</strong> High-concentration subjects (Physics or Math problem solving).</li>
    <li><strong>Block 2 (Afternoon 2:00 PM - 5:30 PM):</strong> Coaching classes or lecture review and class notes revision.</li>
    <li><strong>Block 3 (Evening 7:00 PM - 10:30 PM):</strong> NCERT reading, memorization, and homework problem sheets.</li>
</ul>
<p>Sleep is non-negotiable. Seven hours of deep sleep is essential for the hippocampus to consolidate short-term memories into permanent recall.</p>
""",
                "table_of_contents": [
                    {"id": "the-reality", "title": "The Reality Behind the 14-Hour Myth", "level": 2},
                    {"id": "the-3x4-block", "title": "The 3x4 Block Daily Timetable", "level": 2},
                    {"id": "sleep-importance", "title": "Why Sleep Is Non-Negotiable", "level": 2},
                ],
                "recommended_books": [],
            },
            {
                "slug": "iit-jee-advanced-maths-blueprint-cengage-black-book",
                "title": "IIT-JEE Advanced Maths Blueprint: From RD Sharma to Cengage & Black Book",
                "excerpt": "Cracking JEE Advanced Mathematics requires shifting from formula substitution to rigorous multi-step analytical reasoning. Here is the exact ladder of books to master.",
                "featured_image": "https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=1200&q=80",
                "featured_image_alt": "Mathematics equations and diagrams on a blackboard",
                "primary_category": cats["neet-jee"],
                "author": authors["er-vikramaditya-verma"],
                "is_featured": True,
                "reading_time_minutes": 8,
                "tags": [tags["iit-jee"], tags["mathematics"], tags["book-review"]],
                "seo_title": "JEE Advanced Mathematics Preparation Blueprint & Booklist | EasyToPick",
                "seo_description": "Master IIT-JEE Advanced Maths with Cengage, Vikas Gupta Black Book, and step-by-step problem ladder guide.",
                "content_html": """
<h2>Why JEE Advanced Maths Feels So Demanding</h2>
<p>JEE Main tests speed and standard algorithm execution. In stark contrast, JEE Advanced Mathematics deliberately merges concepts from Coordinate Geometry, Calculus, and Binomial Theorem into single questions designed to punish rote memorization.</p>
<h3>The 3-Tier Book Progression Ladder</h3>
<ul>
    <li><strong>Tier 1 - Conceptual Grounding:</strong> NCERT & RD Sharma Vol 1 & 2 for rigorous algebraic fluency.</li>
    <li><strong>Tier 2 - JEE Main & Intermediate:</strong> Cengage Mathematics series by G. Tewani. Complete all Single Correct and Linked Comprehension exercises.</li>
    <li><strong>Tier 3 - Advanced Mastery:</strong> <em>Advanced Problems in Mathematics</em> by Vikas Gupta & Pankaj Joshi (famously known as the 'Black Book').</li>
</ul>
<blockquote>"If you solve 15 challenging problems where you struggle for 20 minutes each, you learn more than solving 80 easy standard formula questions." — Er. Vikramaditya Verma</blockquote>
""",
                "table_of_contents": [
                    {"id": "why-maths-demanding", "title": "Why JEE Advanced Maths Feels Demanding", "level": 2},
                    {"id": "the-3-tier-ladder", "title": "The 3-Tier Book Progression Ladder", "level": 2},
                ],
                "recommended_books": [
                    {
                        "title": "Advanced Problems in Mathematics (Black Book) by Vikas Gupta",
                        "subtitle": "Balaji Publications • JEE Advanced",
                        "price": "₹620",
                        "originalPrice": "₹750",
                        "discountBadge": "17% OFF",
                        "href": "/products/black-book-maths-vikas-gupta",
                        "image": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=400&q=80",
                        "badge": "Advanced Pick",
                    }
                ],
            },
            {
                "slug": "cbse-class-10-12-board-exam-preparation-integrating-ncert-coaching",
                "title": "CBSE Class 10 & 12 Board Exam Preparation: Integrating NCERT with Entrance Coaching",
                "excerpt": "Don't let board exam subjective writing slip while focusing on competitive MCQs. Learn how to structure derivations, definitions, and score 95%+ in boards.",
                "featured_image": "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?auto=format&fit=crop&w=1200&q=80",
                "featured_image_alt": "Student writing an examination paper with fountain pen",
                "primary_category": cats["study-strategies"],
                "author": authors["priya-rathore"],
                "is_featured": False,
                "reading_time_minutes": 6,
                "tags": [tags["cbse-boards"], tags["ncert-books"], tags["study-routine"]],
                "seo_title": "CBSE Board Exams + Entrance Coaching Integration Guide | EasyToPick",
                "seo_description": "Score 95%+ in CBSE Class 10 & 12 while preparing for NEET or JEE. Balance subjective board answers with objective competitive coaching.",
                "content_html": """
<h2>The Risk of Neglecting Subjective Answer Writing</h2>
<p>Many students scoring top percentile in objective test series lose unexpected marks in CBSE Class 12 Boards simply because competitive preparation focuses on mental shortcuts, while boards require step-by-step formula derivations, unit declarations, and neat circuit diagrams.</p>
<h3>Weekly 2-Hour Subjective Writing Ritual</h3>
<p>Every Saturday evening, spend 2 hours writing out complete previous year board answers with full steps, margins, and labeled pencil diagrams. Review against official CBSE marking schemes.</p>
""",
                "table_of_contents": [
                    {"id": "risk-of-neglect", "title": "The Risk of Neglecting Subjective Writing", "level": 2},
                    {"id": "weekly-ritual", "title": "Weekly 2-Hour Subjective Writing Ritual", "level": 2},
                ],
                "recommended_books": [],
            },
            {
                "slug": "general-science-static-gk-ssc-cgl-railway-exams",
                "title": "General Science & Static GK for SSC CGL & Railway Exams: Scoring 45+ Strategy",
                "excerpt": "A high-yield roadmap to master Lucent GK and NCERT Class 6-10 science concepts for SSC CGL, CHSL, and RRB NTPC examinations.",
                "featured_image": "https://images.unsplash.com/photo-1427504494785-3a9ca7044f45?auto=format&fit=crop&w=1200&q=80",
                "featured_image_alt": "Open notebook with scientific diagrams and national symbols",
                "primary_category": cats["govt-exams"],
                "author": authors["priya-rathore"],
                "is_featured": False,
                "reading_time_minutes": 7,
                "tags": [tags["rajasthan-govt"], tags["cet-exam"], tags["book-review"]],
                "seo_title": "General Science & Static GK Strategy for SSC & Railway Exams | EasyToPick",
                "seo_description": "Score 45+ in General Awareness for SSC CGL, CHSL, and Railway RRB exams with Lucent GK and NCERT science summaries.",
                "content_html": """
<h2>Why General Awareness Decides Merit in SSC & Railways</h2>
<p>Maths and Reasoning have high scoring averages among serious aspirants. The candidate who secures 38 to 44 out of 50 in General Awareness automatically gains an unassailable rank cushion.</p>
<h3>The Lucent + NCERT Fast-Track System</h3>
<p>Cover Physics, Chemistry, and Biology from Lucent's General Knowledge first. Complement this with chapter-wise solved question banks from Kiran or Pinnacle Publications covering TCS exam patterns from 2018 onwards.</p>
""",
                "table_of_contents": [
                    {"id": "why-ga-decides-merit", "title": "Why General Awareness Decides Merit", "level": 2},
                    {"id": "lucent-ncert-system", "title": "The Lucent + NCERT Fast-Track System", "level": 2},
                ],
                "recommended_books": [],
            },
            {
                "slug": "organic-chemistry-reaction-mechanisms-kota-memory-tricks",
                "title": "Organic Chemistry Reaction Mechanisms: Kota Memory Tricks & Best Practice Books",
                "excerpt": "Stop memorizing isolated organic reactions. Understand electron displacement, nucleophilic attack vectors, and build a master flow chart.",
                "featured_image": "https://images.unsplash.com/photo-1603126857599-f6e157fa2fe6?auto=format&fit=crop&w=1200&q=80",
                "featured_image_alt": "Chemical reaction apparatus with colorful solutions",
                "primary_category": cats["neet-jee"],
                "author": authors["amitabh-meena"],
                "is_featured": True,
                "reading_time_minutes": 8,
                "tags": [tags["chemistry"], tags["neet-2026"], tags["iit-jee"], tags["book-review"]],
                "seo_title": "Organic Chemistry Reaction Mechanisms & Memory Tricks | EasyToPick",
                "seo_description": "Master Organic Chemistry for JEE & NEET with Kota faculty reaction mechanism charts, MS Chouhan practice book, and visual summaries.",
                "content_html": """
<h2>Why Students Fear Organic Chemistry</h2>
<p>Most students treat organic chemistry like historical dates to be memorized. When you realize that 90% of all organic reactions are simply nucleophiles (electron-rich species) attacking electrophiles (electron-deficient centers), the subject becomes as predictable and logical as mathematics.</p>
<h3>The 4 Essential Pillars of Reaction Mechanisms</h3>
<ul>
    <li><strong>Inductive, Mesomeric, and Hyperconjugation Effects:</strong> Always determine intermediate carbocation stability before writing products.</li>
    <li><strong>Named Reactions Flow Chart:</strong> Aldol, Cannizzaro, Reimer-Tiemann, and Hoffmann Bromamide should be practiced on a large chart on your wall.</li>
    <li><strong>MS Chouhan Advanced Problems in Organic Chemistry:</strong> The undisputed gold standard for practicing NEET & JEE organic reaction pathways.</li>
</ul>
""",
                "table_of_contents": [
                    {"id": "why-fear-organic", "title": "Why Students Fear Organic Chemistry", "level": 2},
                    {"id": "four-essential-pillars", "title": "The 4 Essential Pillars of Reaction Mechanisms", "level": 2},
                ],
                "recommended_books": [
                    {
                        "title": "Advanced Problems in Organic Chemistry by M.S. Chouhan",
                        "subtitle": "Balaji Publications • Latest Edition",
                        "price": "₹590",
                        "originalPrice": "₹700",
                        "discountBadge": "15% OFF",
                        "href": "/products/ms-chouhan-organic-chemistry",
                        "image": "https://images.unsplash.com/photo-1532012164546-f432f2e3dd45?auto=format&fit=crop&w=400&q=80",
                        "badge": "Top Rated",
                    }
                ],
            },
            {
                "slug": "effective-problem-solving-5-minute-rule-physics-maths",
                "title": "Effective Problem Solving: The 5-Minute Rule for Tough Physics and Mathematics Questions",
                "excerpt": "Looking up solutions too early kills problem intuition. Looking up too late wastes precious hours. Master the Kota 5-minute struggle rule.",
                "featured_image": "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?auto=format&fit=crop&w=1200&q=80",
                "featured_image_alt": "Thoughtful student working through difficult numerical problems",
                "primary_category": cats["study-strategies"],
                "author": authors["dr-rajesh-sharma"],
                "is_featured": False,
                "reading_time_minutes": 5,
                "tags": [tags["study-routine"], tags["physics"], tags["mathematics"], tags["kota-mentors"]],
                "seo_title": "The 5-Minute Problem Solving Rule for Physics & Maths | EasyToPick",
                "seo_description": "Build deep mathematical intuition with the 5-Minute Struggle Rule used by Kota coaching toppers for Physics and Mathematics.",
                "content_html": """
<h2>The Counter-Productive Solution Trap</h2>
<p>When you get stuck on a difficult physics or math problem, glancing at the hint or answer key after 60 seconds triggers a psychological illusion: <em>"Oh yes, of course, I would have thought of that next."</em> You wouldn't have! Your neural pathways only grow when you wrestle with ambiguity.</p>
<h3>How the 5-Minute Rule Works</h3>
<ol>
    <li>Set a timer for 5 minutes. Close all solution manuals.</li>
    <li>Draw a fresh diagram. Write down all given variables and all conservation laws that might connect them.</li>
    <li>Try at least 2 alternate approaches (e.g. Work-Energy theorem instead of Newton's Laws).</li>
    <li>Only after the timer beeps and your page is filled with earnest attempts may you review the first line of the solution.</li>
</ol>
""",
                "table_of_contents": [
                    {"id": "solution-trap", "title": "The Counter-Productive Solution Trap", "level": 2},
                    {"id": "how-it-works", "title": "How the 5-Minute Rule Works", "level": 2},
                ],
                "recommended_books": [],
            },
        ]

        now = timezone.now()
        for i, pdata in enumerate(posts_data):
            post, created = BlogPost.objects.update_or_create(
                slug=pdata["slug"],
                defaults={
                    "title": pdata["title"],
                    "excerpt": pdata["excerpt"],
                    "content": pdata["content_html"],
                    "content_html": pdata["content_html"],
                    "status": BlogPostStatus.PUBLISHED,
                    "featured_image": pdata["featured_image"],
                    "featured_image_alt": pdata["featured_image_alt"],
                    "primary_category": pdata["primary_category"],
                    "author": pdata["author"],
                    "is_featured": pdata["is_featured"],
                    "reading_time_minutes": pdata["reading_time_minutes"],
                    "published_at": now - timezone.timedelta(days=i),
                    "seo_title": pdata["seo_title"],
                    "seo_description": pdata["seo_description"],
                    "table_of_contents": pdata["table_of_contents"],
                    "recommended_books": pdata["recommended_books"],
                    "robots_index": True,
                    "robots_follow": True,
                },
            )
            post.categories.set([pdata["primary_category"]])
            post.tags.set(pdata["tags"])
            if created or not post.revisions.exists():
                post.create_revision()

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(posts_data)} educational blogs!"))
