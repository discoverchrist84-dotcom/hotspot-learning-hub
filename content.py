"""Editable site content. Change text here; swap images by replacing the files in static/team/."""

# The waitlist form and the course section both read this list.
COURSES = [
    {"name": "Python Programming", "icon": "🐍", "blurb": "Build real programs from scratch"},
    {"name": "Graphics Design", "icon": "🎨", "blurb": "Logos, posters and brand visuals"},
    {"name": "Video Editing", "icon": "🎬", "blurb": "Cut, polish and publish great videos"},
    {"name": "AI Automation", "icon": "🤖", "blurb": "Automate everyday work with AI tools"},
    {"name": "Microsoft Application Packages", "icon": "🧰", "blurb": "Word, Excel, PowerPoint and more"},
    {"name": "Cyber Security", "icon": "🛡️", "blurb": "Protect systems, data and people"},
    {"name": "Presentation", "icon": "🎤", "blurb": "Present with confidence, including live production tools like vMix"},
    {"name": "Data Analysis", "icon": "📊", "blurb": "Turn raw data into decisions"},
]

# Names used by earlier signups. They stay in the admin dashboard but are not offered on the form.
LEGACY_COURSES = {"Video Editing/AI Automation": "🎬"}

# Set "revealed": True and replace the image when you are ready to reveal a person.
COHOSTS = [
    {"name": "8Digits Komputers", "role": "Cohost", "note": "", "image": "team/cohost-8digits.jpg", "revealed": True},
    {"name": "Black Media", "role": "Cohost", "note": "", "image": "team/cohost-black-media.jpg", "revealed": False},
]
SPONSORS = [
    {"name": "Davis", "role": "Sponsor", "note": "", "image": "team/sponsor-davis.jpg", "revealed": True},
    {"name": "Course Advisor", "role": "Sponsor", "note": "200L CMP · Vortex Network", "image": "team/sponsor-advisor.jpg", "revealed": False},
]


# Sessions, shown in the hero and on the success page. Empty this list to show the "coming soon" banner again.
SCHEDULE = [
    {"day": "Saturdays", "time": "10AM", "venue": "Old COLPAS"},
    {"day": "Sundays", "time": "2PM", "venue": "Old COLPAS"},
]

# Official lecture timetable. "course" must match a course name in COURSES.
TIMETABLE = [
    {"day": "Saturdays", "venue": "Old COLPAS", "slots": [
        {"course": "Python Programming", "time": "10:00AM - 12:00PM"},
        {"course": "Cyber Security", "time": "12:00PM - 2:00PM"},
    ]},
    {"day": "Sundays", "venue": "Old COLPAS", "slots": [
        {"course": "Graphics Design", "time": "2:00PM - 4:00PM"},
        {"course": "AI Automation", "time": "4:00PM - 6:00PM"},
    ]},
]
