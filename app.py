
# --- Imports ---
import os
import csv
import re
import traceback
import streamlit as st
import torch

# --- Page config ---
st.set_page_config(page_title="SellSpark", page_icon="🛍️", layout="wide")

# --- Secrets access ---
hf_token = st.secrets.get("HF_TOKEN", None)
if not hf_token:
    st.error("❌ Missing HF_TOKEN in st.secrets. Add it locally or in Hugging Face Secrets.")
    st.stop()

# --- Mode (fixed, no Fast/Premium toggle) ---
mode = "Fast"   # keep this so optimize_listing still works

# --- Branding visuals (logo + banner) ---
st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)

if os.path.exists("sellspark_logo.png"):
    st.image("sellspark_logo.png", use_container_width=True)

if os.path.exists("sellspark_banner.png"):
    st.image("sellspark_banner.png", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# --- Tone Selection ---
st.markdown("### 🎯 Tone Selection")
st.caption("Choose the communication style you want for your optimized listing.")

styles = ["Persuasive", "Casual", "Luxury", "Urgent", "Tech-savvy"]
if "selected_style" not in st.session_state:
    st.session_state.selected_style = styles[0]

tone = st.radio(
    "Pick a tone:",
    styles,
    index=styles.index(st.session_state.selected_style),
    horizontal=True,
    key="tone_selector"
)
st.session_state.selected_style = tone

# --- Listing Input ---
st.markdown("### 🛍️ Listing Optimization")
st.caption("Paste one or more product listings (one per line).")

input_text = st.text_area(
    "📝 Enter your listing(s):",
    height=300,
    value=st.session_state.get("bulk_input", ""),
    key="listing_input"
)

# --- Default fallback template ---
DEFAULT_TEMPLATE = {
    "Persuasive": ["Experience the difference with", "Built to last, easy to use, and ready to impress."],
    "Casual": ["Say hello to your new favorite", "Simple, reliable, and made for everyday life."],
    "Luxury": ["Indulge in the elegance of", "Crafted for those who appreciate the finer things."],
    "Urgent": ["Don’t miss out on", "Limited stock — grab yours before it's gone!"],
    "Tech-savvy": ["Engineered for performance:", "Smart, sleek, and built for modern living."]
}

REWRITE_TEMPLATES = {
    # 1. Food & Beverage
    "Food & Beverage": {
        "Persuasive": [
            "Savor the irresistible taste of {keyword} — crafted to delight every bite.",
            "Order {keyword} today and experience flavor that speaks for itself."
        ],
        "Casual": [
            "Grab a quick bite of {keyword} — simple, tasty, and ready when you are.",
            "Made for everyday cravings, {keyword} fits right into your routine."
        ],
        "Luxury": [
            "Indulge in gourmet {keyword}, a culinary masterpiece for refined palates.",
            "Elevate your dining with {keyword} — crafted for unforgettable moments."
        ],
        "Urgent": [
            "Hungry now? {keyword} is waiting — don’t miss your chance to enjoy it.",
            "Act fast! {keyword} is flying off the shelves — grab yours before it’s gone."
        ],
        "Tech-savvy": [
            "Digitally delicious: {keyword}, optimized for modern taste and convenience.",
            "Smart flavor meets innovation — {keyword} redefines how you enjoy food."
        ]
    },

    # 2. Jewelry
    "Jewelry": {
        "Persuasive": [
            "Make a bold statement with {keyword} — elegance that never fades.",
            "Turn every glance into admiration with {keyword}."
        ],
        "Casual": [
            "Shine bright every day with {keyword} — stylish, simple, stunning.",
            "Add a touch of sparkle to your look with {keyword}."
        ],
        "Luxury": [
            "Discover timeless beauty in {keyword}, crafted for true connoisseurs.",
            "Hand‑crafted brilliance — {keyword} is luxury redefined."
        ],
        "Urgent": [
            "Limited edition {keyword} — secure your sparkle today.",
            "Don’t wait — {keyword} is almost gone, claim yours now."
        ],
        "Tech-savvy": [
            "Precision meets elegance: {keyword}, designed with cutting‑edge artistry.",
            "Where innovation meets brilliance — {keyword} is engineered to shine."
        ]
    },

    # 3. Health & Medicine
    "Health & Medicine": {
        "Persuasive": [
            "Feel your best with {keyword} — trusted by professionals worldwide.",
            "Choose {keyword} for care that puts your health first."
        ],
        "Casual": [
            "Stay healthy with {keyword} — simple relief for everyday life.",
            "Your wellness, made easy with {keyword}."
        ],
        "Luxury": [
            "Premium care begins with {keyword} — wellness redefined for you.",
            "Experience the gold standard of health with {keyword}."
        ],
        "Urgent": [
            "Act fast — relief with {keyword} is just a dose away.",
            "Don’t wait to feel better: {keyword} is here for you now."
        ],
        "Tech-savvy": [
            "Clinically smart: {keyword}, engineered for modern health needs.",
            "Innovation meets care — {keyword} is science you can trust."
        ]
    },

    # 4. Electronics
    "Electronics": {
        "Persuasive": [
            "Upgrade your life with {keyword} — performance meets innovation.",
            "Discover the power of {keyword}, built to impress and endure."
        ],
        "Casual": [
            "Plug in and enjoy {keyword} — smart, simple, reliable.",
            "Everyday tech made easy with {keyword}."
        ],
        "Luxury": [
            "Elite technology, timeless design — {keyword} sets you apart.",
            "Experience distinction with {keyword}, crafted for the few who demand more."
        ],
        "Urgent": [
            "Don’t miss this drop: {keyword} is selling fast.",
            "Limited stock alert — secure your {keyword} today."
        ],
        "Tech-savvy": [
            "Engineered for excellence: {keyword}, built for modern living.",
            "Smart design, powerful performance — {keyword} is future‑ready."
        ]
    },

    # 5. Fashion & Apparel
    "Fashion & Apparel": {
        "Persuasive": [
            "Step out in style with {keyword} — designed to turn heads.",
            "Upgrade your wardrobe with {keyword}, where comfort meets confidence."
        ],
        "Casual": [
            "Keep it cool and comfy with {keyword}.",
            "Everyday style made simple — {keyword} fits right in."
        ],
        "Luxury": [
            "Elevate your look with {keyword}, crafted with timeless elegance.",
            "Experience couture‑level detail in every {keyword}."
        ],
        "Urgent": [
            "Trending now: {keyword} — don’t miss your chance to own it.",
            "Hot drop alert! {keyword} is almost gone."
        ],
        "Tech-savvy": [
            "Smart fashion meets innovation — {keyword} adapts to your lifestyle.",
            "Engineered for comfort and style: {keyword} is future‑ready apparel."
        ]
    },
    
# 6. Home & Kitchen
"Home & Kitchen": {
    "Persuasive": [
        "Transform your space with {keyword} — where function meets beauty.",
        "Upgrade your home experience with {keyword}, designed to impress daily."
    ],
    "Casual": [
        "Make life easier with {keyword} — simple, handy, and reliable.",
        "Everyday comfort starts with {keyword} in your home."
    ],
    "Luxury": [
        "Elevate your living with {keyword}, crafted for timeless elegance.",
        "Experience premium design and comfort with {keyword}."
    ],
    "Urgent": [
        "Limited stock of {keyword} — upgrade your home today.",
        "Don’t wait — {keyword} is selling fast, secure yours now."
    ],
    "Tech-savvy": [
        "Smart living starts with {keyword}, engineered for modern homes.",
        "Innovation meets comfort — {keyword} redefines home essentials."
    ]
},

# 7. Beauty & Personal Care
"Beauty & Personal Care": {
    "Persuasive": [
        "Reveal your best self with {keyword} — beauty that lasts.",
        "Enhance your routine with {keyword}, trusted by professionals."
    ],
    "Casual": [
        "Glow up with {keyword} — simple, fun, and effective.",
        "Everyday care made easy with {keyword}."
    ],
    "Luxury": [
        "Indulge in the elegance of {keyword}, crafted for radiant beauty.",
        "Experience spa‑like luxury at home with {keyword}."
    ],
    "Urgent": [
        "Hot beauty pick: {keyword} — get it before it’s gone.",
        "Act fast — {keyword} is trending and selling quickly."
    ],
    "Tech-savvy": [
        "Smart skincare starts with {keyword}, powered by innovation.",
        "Engineered for results — {keyword} blends science with beauty."
    ]
},

# 8. Sports & Outdoors
"Sports & Outdoors": {
    "Persuasive": [
        "Push your limits with {keyword} — built for performance.",
        "Achieve more with {keyword}, trusted by athletes worldwide."
    ],
    "Casual": [
        "Get moving with {keyword} — fun, simple, and reliable.",
        "Adventure made easy with {keyword} by your side."
    ],
    "Luxury": [
        "Experience elite performance with {keyword}, crafted for champions.",
        "Premium gear for premium results — {keyword} sets you apart."
    ],
    "Urgent": [
        "Gear up now — {keyword} is almost gone.",
        "Don’t miss your chance to own {keyword} today."
    ],
    "Tech-savvy": [
        "Engineered for endurance — {keyword} is built with cutting‑edge tech.",
        "Smart design meets performance: {keyword} is future‑ready gear."
    ]
},

# 9. Toys & Games
"Toys & Games": {
    "Persuasive": [
        "Bring joy home with {keyword} — fun for all ages.",
        "Create unforgettable moments with {keyword}."
    ],
    "Casual": [
        "Playtime made better with {keyword}.",
        "Simple fun, endless smiles — that’s {keyword}."
    ],
    "Luxury": [
        "Discover premium play with {keyword}, crafted for lasting memories.",
        "Elevate playtime with {keyword}, designed with care and detail."
    ],
    "Urgent": [
        "Hot toy alert: {keyword} — grab it before it’s gone.",
        "Don’t wait — {keyword} is flying off the shelves."
    ],
    "Tech-savvy": [
        "Smart play begins with {keyword}, blending fun and innovation.",
        "Interactive, modern, and exciting — {keyword} is play reimagined."
    ]
},

# 10. Books & Media
"Books & Media": {
    "Persuasive": [
        "Unlock new worlds with {keyword} — stories that inspire.",
        "Expand your mind with {keyword}, crafted to captivate."
    ],
    "Casual": [
        "Relax and enjoy {keyword} — your perfect escape.",
        "Everyday entertainment made easy with {keyword}."
    ],
    "Luxury": [
        "Experience the art of storytelling with {keyword}, a timeless treasure.",
        "Premium editions of {keyword} — crafted for collectors."
    ],
    "Urgent": [
        "Limited release: {keyword} — get your copy today.",
        "Don’t miss out — {keyword} is in high demand."
    ],
    "Tech-savvy": [
        "Digital meets imagination — {keyword} is optimized for modern readers.",
        "Smart, portable, and engaging — {keyword} brings stories to life."
    ]
},
    
# 11. Automotive
"Automotive": {
    "Persuasive": [
        "Drive with confidence in {keyword} — engineered for performance.",
        "Upgrade your ride with {keyword}, built to go the distance."
    ],
    "Casual": [
        "Hit the road with {keyword} — simple, smooth, and reliable.",
        "Everyday driving made easy with {keyword}."
    ],
    "Luxury": [
        "Experience prestige behind the wheel with {keyword}.",
        "Crafted for elegance and power — {keyword} redefines driving."
    ],
    "Urgent": [
        "Limited stock of {keyword} — secure yours today.",
        "Don’t wait — {keyword} is moving fast off the lot."
    ],
    "Tech-savvy": [
        "Smart engineering meets innovation — {keyword} is future‑ready.",
        "Advanced design, powerful performance — {keyword} leads the way."
    ]
},

# 12. Office Supplies
"Office Supplies": {
    "Persuasive": [
        "Boost productivity with {keyword} — tools that work as hard as you do.",
        "Stay organized and efficient with {keyword}."
    ],
    "Casual": [
        "Make workdays smoother with {keyword}.",
        "Simple, reliable, and handy — that’s {keyword}."
    ],
    "Luxury": [
        "Elevate your workspace with {keyword}, crafted for professionals.",
        "Premium quality meets everyday function — {keyword} delivers."
    ],
    "Urgent": [
        "Running low? Restock {keyword} before it’s gone.",
        "Act now — {keyword} is in high demand."
    ],
    "Tech-savvy": [
        "Smart office solutions start with {keyword}.",
        "Engineered for efficiency — {keyword} keeps you ahead."
    ]
},

# 13. Pet Supplies
"Pet Supplies": {
    "Persuasive": [
        "Give your pet the best with {keyword} — because they deserve it.",
        "Happy pets start with {keyword}, trusted by owners everywhere."
    ],
    "Casual": [
        "Treat your furry friend with {keyword}.",
        "Everyday care made easy with {keyword}."
    ],
    "Luxury": [
        "Indulge your pet with {keyword}, crafted for comfort and joy.",
        "Premium care for your companion — {keyword} makes the difference."
    ],
    "Urgent": [
        "Don’t let your pet miss out — {keyword} is going fast.",
        "Stock up now on {keyword} before it’s gone."
    ],
    "Tech-savvy": [
        "Smart pet care starts with {keyword}.",
        "Innovative design for happy pets — {keyword} is the future of care."
    ]
},

# 14. Baby Products
"Baby Products": {
    "Persuasive": [
        "Give your little one the best start with {keyword}.",
        "Trusted by parents worldwide — {keyword} cares for your baby."
    ],
    "Casual": [
        "Keep baby happy and comfy with {keyword}.",
        "Everyday parenting made easier with {keyword}."
    ],
    "Luxury": [
        "Premium comfort for your baby — {keyword} sets the standard.",
        "Crafted with care, {keyword} brings elegance to baby essentials."
    ],
    "Urgent": [
        "Don’t wait — {keyword} is a must‑have for parents now.",
        "Limited stock of {keyword} — order today."
    ],
    "Tech-savvy": [
        "Smart parenting starts with {keyword}.",
        "Engineered for safety and comfort — {keyword} is future‑ready."
    ]
},

# 15. Musical Instruments
"Musical Instruments": {
    "Persuasive": [
        "Unleash your creativity with {keyword} — crafted for musicians.",
        "Make every note count with {keyword}, trusted by performers."
    ],
    "Casual": [
        "Play your heart out with {keyword}.",
        "Simple, fun, and expressive — that’s {keyword}."
    ],
    "Luxury": [
        "Experience artistry in sound with {keyword}.",
        "Premium craftsmanship meets timeless music — {keyword} inspires."
    ],
    "Urgent": [
        "Hot pick for musicians: {keyword} — get yours today.",
        "Don’t miss out — {keyword} is in high demand."
    ],
    "Tech-savvy": [
        "Smart sound starts with {keyword}, engineered for precision.",
        "Innovation meets harmony — {keyword} is music reimagined."
    ]
},
# 16. Gardening & Outdoors
"Gardening & Outdoors": {
    "Persuasive": [
        "Grow with confidence using {keyword} — trusted by green thumbs everywhere.",
        "Transform your outdoor space with {keyword}, built for lasting beauty."
    ],
    "Casual": [
        "Make gardening easy with {keyword}.",
        "Fresh air, fresh blooms — {keyword} helps you enjoy it all."
    ],
    "Luxury": [
        "Elevate your garden with {keyword}, crafted for timeless elegance.",
        "Premium tools and design — {keyword} makes every garden flourish."
    ],
    "Urgent": [
        "Spring is here — grab {keyword} before it’s gone.",
        "Limited stock of {keyword} — plant your success today."
    ],
    "Tech-savvy": [
        "Smart gardening starts with {keyword}, engineered for efficiency.",
        "Innovation meets nature — {keyword} redefines outdoor living."
    ]
},

# 17. Travel & Luggage
"Travel & Luggage": {
    "Persuasive": [
        "Travel smarter with {keyword} — built for every journey.",
        "Adventure awaits — pack with {keyword} and go further."
    ],
    "Casual": [
        "Hit the road with {keyword} — simple, sturdy, and ready.",
        "Travel made easy with {keyword} by your side."
    ],
    "Luxury": [
        "Experience first‑class travel with {keyword}, crafted for elegance.",
        "Premium journeys begin with {keyword} — style meets durability."
    ],
    "Urgent": [
        "Trip coming up? Don’t wait — grab {keyword} today.",
        "Limited edition {keyword} — secure yours before your next adventure."
    ],
    "Tech-savvy": [
        "Smart travel starts with {keyword}, engineered for convenience.",
        "Innovation on the move — {keyword} is luggage reimagined."
    ]
},

# 18. Furniture
"Furniture": {
    "Persuasive": [
        "Redefine your space with {keyword} — comfort meets design.",
        "Upgrade your home with {keyword}, built to last and impress."
    ],
    "Casual": [
        "Relax in style with {keyword}.",
        "Everyday comfort made simple — {keyword} fits right in."
    ],
    "Luxury": [
        "Experience timeless elegance with {keyword}, crafted for distinction.",
        "Premium design and craftsmanship — {keyword} transforms your home."
    ],
    "Urgent": [
        "Limited stock of {keyword} — upgrade your space today.",
        "Don’t wait — {keyword} is selling fast."
    ],
    "Tech-savvy": [
        "Smart living starts with {keyword}, engineered for modern homes.",
        "Innovation meets comfort — {keyword} is furniture redefined."
    ]
},

# 19. Art & Collectibles
"Art & Collectibles": {
    "Persuasive": [
        "Own a masterpiece with {keyword} — art that inspires.",
        "Add timeless value to your collection with {keyword}."
    ],
    "Casual": [
        "Brighten your space with {keyword}.",
        "Simple, stylish, and unique — {keyword} makes a statement."
    ],
    "Luxury": [
        "Indulge in the elegance of {keyword}, crafted for true collectors.",
        "Premium artistry meets timeless design — {keyword} is unforgettable."
    ],
    "Urgent": [
        "Rare find: {keyword} — secure it before it’s gone.",
        "Don’t miss your chance to own {keyword} today."
    ],
    "Tech-savvy": [
        "Digital meets design — {keyword} is art for the modern age.",
        "Smart collecting starts with {keyword}, blending tradition and tech."
    ]
},

# 20. Stationery & Crafts
"Stationery & Crafts": {
    "Persuasive": [
        "Create with confidence using {keyword} — tools that inspire.",
        "Bring your ideas to life with {keyword}, trusted by creators."
    ],
    "Casual": [
        "Make every project fun with {keyword}.",
        "Simple, colorful, and creative — {keyword} is made for you."
    ],
    "Luxury": [
        "Elevate your craft with {keyword}, crafted for perfection.",
        "Premium quality meets creativity — {keyword} inspires brilliance."
    ],
    "Urgent": [
        "Hot pick for creators: {keyword} — get yours today.",
        "Don’t wait — {keyword} is selling fast."
    ],
    "Tech-savvy": [
        "Smart creativity starts with {keyword}, engineered for precision.",
        "Innovation meets artistry — {keyword} is crafting reimagined."
    ]
},
# 21. Appliances
"Appliances": {
    "Persuasive": [
        "Simplify your life with {keyword} — built for everyday efficiency.",
        "Upgrade your home with {keyword}, trusted for performance and durability."
    ],
    "Casual": [
        "Make chores easier with {keyword}.",
        "Everyday convenience starts with {keyword}."
    ],
    "Luxury": [
        "Experience premium living with {keyword}, crafted for elegance and power.",
        "Redefine home comfort with {keyword}, designed for distinction."
    ],
    "Urgent": [
        "Hot pick: {keyword} — limited stock available.",
        "Don’t wait — {keyword} is selling fast."
    ],
    "Tech-savvy": [
        "Smart homes start with {keyword}, engineered for innovation.",
        "Future‑ready design meets everyday use — {keyword} delivers."
    ]
},

# 22. Industrial & Tools
"Industrial & Tools": {
    "Persuasive": [
        "Get the job done right with {keyword} — built for professionals.",
        "Power through any task with {keyword}, trusted worldwide."
    ],
    "Casual": [
        "Work smarter with {keyword}.",
        "Everyday projects made easy with {keyword}."
    ],
    "Luxury": [
        "Premium strength and precision — {keyword} sets the standard.",
        "Crafted for excellence, {keyword} delivers unmatched performance."
    ],
    "Urgent": [
        "Don’t miss out — {keyword} is in high demand.",
        "Act fast — {keyword} is almost gone."
    ],
    "Tech-savvy": [
        "Engineered for precision — {keyword} is built with cutting‑edge tech.",
        "Smart tools for smarter work — {keyword} redefines efficiency."
    ]
},

# 23. Groceries
"Groceries": {
    "Persuasive": [
        "Stock your pantry with {keyword} — fresh, reliable, and delicious.",
        "Every meal gets better with {keyword}, trusted by families."
    ],
    "Casual": [
        "Grab {keyword} for your everyday needs.",
        "Simple, tasty, and ready — {keyword} fits right in."
    ],
    "Luxury": [
        "Indulge in premium {keyword}, crafted for refined taste.",
        "Experience gourmet quality with {keyword}."
    ],
    "Urgent": [
        "Fresh stock of {keyword} won’t last long — order now.",
        "Don’t wait — {keyword} is selling quickly."
    ],
    "Tech-savvy": [
        "Smart shopping starts with {keyword}, optimized for freshness.",
        "Innovation meets flavor — {keyword} is grocery reimagined."
    ]
},

# 24. Footwear
"Footwear": {
    "Persuasive": [
        "Step into comfort and style with {keyword}.",
        "Upgrade your stride with {keyword}, built for performance."
    ],
    "Casual": [
        "Everyday comfort starts with {keyword}.",
        "Keep it simple, stylish, and comfy with {keyword}."
    ],
    "Luxury": [
        "Experience timeless elegance with {keyword}, crafted for distinction.",
        "Premium design meets comfort — {keyword} redefines footwear."
    ],
    "Urgent": [
        "Hot drop: {keyword} — sizes selling fast.",
        "Don’t miss out — {keyword} is almost gone."
    ],
    "Tech-savvy": [
        "Smart design meets innovation — {keyword} is future‑ready footwear.",
        "Engineered for performance and comfort — {keyword} delivers."
    ]
},

# 25. Watches
"Watches": {
    "Persuasive": [
        "Make every moment count with {keyword}.",
        "Upgrade your style with {keyword}, crafted for precision."
    ],
    "Casual": [
        "Keep it cool and stylish with {keyword}.",
        "Everyday timekeeping made easy with {keyword}."
    ],
    "Luxury": [
        "Experience timeless elegance with {keyword}, designed for connoisseurs.",
        "Premium craftsmanship meets precision — {keyword} is luxury redefined."
    ],
    "Urgent": [
        "Limited edition {keyword} — secure yours today.",
        "Don’t wait — {keyword} is selling fast."
    ],
    "Tech-savvy": [
        "Smart timekeeping starts with {keyword}, engineered for innovation.",
        "Future‑ready design meets precision — {keyword} is watchmaking reimagined."
    ]
},
# 26. Gaming
"Gaming": {
    "Persuasive": [
        "Level up your play with {keyword} — built for champions.",
        "Experience next‑level fun with {keyword}, trusted by gamers worldwide."
    ],
    "Casual": [
        "Game on with {keyword} — simple, fun, and exciting.",
        "Everyday entertainment made better with {keyword}."
    ],
    "Luxury": [
        "Indulge in elite gaming with {keyword}, crafted for serious players.",
        "Premium performance meets immersive design — {keyword} delivers."
    ],
    "Urgent": [
        "Hot release: {keyword} — grab it before it’s gone.",
        "Don’t wait — {keyword} is selling fast."
    ],
    "Tech-savvy": [
        "Engineered for speed and precision — {keyword} redefines gaming.",
        "Smart design meets powerful performance — {keyword} is future‑ready."
    ]
},

# 27. Fitness & Wellness
"Fitness & Wellness": {
    "Persuasive": [
        "Achieve your goals with {keyword} — built for results.",
        "Transform your routine with {keyword}, trusted by fitness enthusiasts."
    ],
    "Casual": [
        "Stay active and healthy with {keyword}.",
        "Everyday wellness made simple with {keyword}."
    ],
    "Luxury": [
        "Elevate your fitness with {keyword}, crafted for premium performance.",
        "Experience elite wellness with {keyword}, designed for distinction."
    ],
    "Urgent": [
        "Don’t wait — {keyword} is your key to results now.",
        "Hot pick: {keyword} — limited stock available."
    ],
    "Tech-savvy": [
        "Smart fitness starts with {keyword}, engineered for precision.",
        "Innovation meets health — {keyword} is wellness reimagined."
    ]
},

# 28. Travel Accessories
"Travel Accessories": {
    "Persuasive": [
        "Travel smarter with {keyword} — built for convenience.",
        "Make every journey easier with {keyword}, trusted by travelers."
    ],
    "Casual": [
        "Pack light, travel right with {keyword}.",
        "Everyday adventures made simple with {keyword}."
    ],
    "Luxury": [
        "Experience first‑class travel with {keyword}, crafted for elegance.",
        "Premium journeys begin with {keyword} — style meets practicality."
    ],
    "Urgent": [
        "Trip coming up? Don’t wait — grab {keyword} today.",
        "Limited stock of {keyword} — secure yours now."
    ],
    "Tech-savvy": [
        "Smart travel starts with {keyword}, engineered for modern explorers.",
        "Innovation on the go — {keyword} redefines travel essentials."
    ]
},

# 29. Cleaning Supplies
"Cleaning Supplies": {
    "Persuasive": [
        "Make every surface shine with {keyword} — trusted for results.",
        "Upgrade your cleaning routine with {keyword}, built for efficiency."
    ],
    "Casual": [
        "Keep it clean and simple with {keyword}.",
        "Everyday messes made easy with {keyword}."
    ],
    "Luxury": [
        "Experience spotless luxury with {keyword}, crafted for perfection.",
        "Premium cleaning power meets elegance — {keyword} delivers."
    ],
    "Urgent": [
        "Running low? Restock {keyword} before it’s gone.",
        "Act fast — {keyword} is in high demand."
    ],
    "Tech-savvy": [
        "Smart cleaning starts with {keyword}, engineered for performance.",
        "Innovation meets hygiene — {keyword} redefines clean."
    ]
},

# 30. Seasonal & Holiday
"Seasonal & Holiday": {
    "Persuasive": [
        "Celebrate in style with {keyword} — memories start here.",
        "Make every occasion special with {keyword}, crafted for joy."
    ],
    "Casual": [
        "Get festive with {keyword} — simple, fun, and cheerful.",
        "Everyday celebrations made brighter with {keyword}."
    ],
    "Luxury": [
        "Indulge in holiday elegance with {keyword}, designed for timeless moments.",
        "Premium celebrations begin with {keyword}."
    ],
    "Urgent": [
        "Holiday rush: {keyword} — order before it’s gone.",
        "Limited edition {keyword} — secure yours today."
    ],
    "Tech-savvy": [
        "Smart celebrations start with {keyword}, optimized for convenience.",
        "Innovation meets tradition — {keyword} redefines festive living."
    ]
},
# 31. Photography & Cameras
"Photography & Cameras": {
    "Persuasive": [
        "Capture every moment with {keyword} — clarity that inspires.",
        "Upgrade your shots with {keyword}, trusted by professionals worldwide."
    ],
    "Casual": [
        "Snap memories with {keyword} — simple, fun, and reliable.",
        "Everyday photography made easy with {keyword}."
    ],
    "Luxury": [
        "Experience artistry in every frame with {keyword}.",
        "Premium craftsmanship meets precision — {keyword} redefines photography."
    ],
    "Urgent": [
        "Hot release: {keyword} — limited stock available.",
        "Don’t miss your chance to own {keyword} today."
    ],
    "Tech-savvy": [
        "Smart imaging starts with {keyword}, engineered for innovation.",
        "Future‑ready design meets precision — {keyword} is photography reimagined."
    ]
},

# 32. Musical Accessories
"Musical Accessories": {
    "Persuasive": [
        "Perfect your performance with {keyword} — built for musicians.",
        "Enhance your sound with {keyword}, trusted by artists everywhere."
    ],
    "Casual": [
        "Jam with ease using {keyword}.",
        "Everyday music made better with {keyword}."
    ],
    "Luxury": [
        "Elevate your performance with {keyword}, crafted for distinction.",
        "Premium design meets sound — {keyword} inspires brilliance."
    ],
    "Urgent": [
        "Hot pick: {keyword} — limited stock available.",
        "Don’t wait — {keyword} is selling fast."
    ],
    "Tech-savvy": [
        "Smart sound starts with {keyword}, engineered for precision.",
        "Innovation meets harmony — {keyword} is music reimagined."
    ]
},

# 33. Smart Home Devices
"Smart Home Devices": {
    "Persuasive": [
        "Transform your living with {keyword} — convenience at your command.",
        "Upgrade your home with {keyword}, trusted for innovation."
    ],
    "Casual": [
        "Make life easier with {keyword}.",
        "Everyday comfort starts with {keyword}."
    ],
    "Luxury": [
        "Experience modern elegance with {keyword}, crafted for distinction.",
        "Premium living begins with {keyword}."
    ],
    "Urgent": [
        "Hot tech drop: {keyword} — order before it’s gone.",
        "Don’t wait — {keyword} is in high demand."
    ],
    "Tech-savvy": [
        "Smart living starts with {keyword}, engineered for efficiency.",
        "Innovation meets comfort — {keyword} redefines home living."
    ]
},

# 34. Office Furniture
"Office Furniture": {
    "Persuasive": [
        "Boost productivity with {keyword} — designed for professionals.",
        "Upgrade your workspace with {keyword}, built for comfort and style."
    ],
    "Casual": [
        "Work smarter with {keyword}.",
        "Everyday comfort made simple with {keyword}."
    ],
    "Luxury": [
        "Experience premium design with {keyword}, crafted for distinction.",
        "Elevate your office with {keyword} — where comfort meets elegance."
    ],
    "Urgent": [
        "Limited stock of {keyword} — upgrade your office today.",
        "Don’t wait — {keyword} is selling fast."
    ],
    "Tech-savvy": [
        "Smart work starts with {keyword}, engineered for efficiency.",
        "Innovation meets productivity — {keyword} is office reimagined."
    ]
},

# 35. Automotive Accessories
"Automotive Accessories": {
    "Persuasive": [
        "Upgrade your drive with {keyword} — built for performance.",
        "Enhance every journey with {keyword}, trusted by drivers worldwide."
    ],
    "Casual": [
        "Hit the road with {keyword} — simple, handy, and reliable.",
        "Everyday driving made better with {keyword}."
    ],
    "Luxury": [
        "Experience premium comfort with {keyword}, crafted for distinction.",
        "Elevate your ride with {keyword} — where style meets function."
    ],
    "Urgent": [
        "Hot pick: {keyword} — limited stock available.",
        "Don’t wait — {keyword} is selling fast."
    ],
    "Tech-savvy": [
        "Smart driving starts with {keyword}, engineered for innovation.",
        "Future‑ready design meets performance — {keyword} delivers."
    ]
},
# 36. Kitchenware
"Kitchenware": {
    "Persuasive": [
        "Cook with confidence using {keyword} — trusted by chefs everywhere.",
        "Upgrade your kitchen with {keyword}, built for performance and style."
    ],
    "Casual": [
        "Make cooking easy with {keyword}.",
        "Everyday meals made simple with {keyword}."
    ],
    "Luxury": [
        "Experience gourmet precision with {keyword}, crafted for elegance.",
        "Premium design meets function — {keyword} elevates your kitchen."
    ],
    "Urgent": [
        "Hot pick: {keyword} — limited stock available.",
        "Don’t wait — {keyword} is selling fast."
    ],
    "Tech-savvy": [
        "Smart cooking starts with {keyword}, engineered for efficiency.",
        "Innovation meets flavor — {keyword} redefines kitchen essentials."
    ]
},

# 37. Lighting
"Lighting": {
    "Persuasive": [
        "Brighten your world with {keyword} — designed to inspire.",
        "Transform your space with {keyword}, crafted for brilliance."
    ],
    "Casual": [
        "Light up your life with {keyword}.",
        "Everyday comfort starts with {keyword}."
    ],
    "Luxury": [
        "Experience timeless elegance with {keyword}, crafted for distinction.",
        "Premium design meets illumination — {keyword} shines bright."
    ],
    "Urgent": [
        "Limited stock of {keyword} — brighten your home today.",
        "Don’t wait — {keyword} is in high demand."
    ],
    "Tech-savvy": [
        "Smart lighting starts with {keyword}, engineered for efficiency.",
        "Innovation meets ambiance — {keyword} redefines illumination."
    ]
},

# 38. Bags & Backpacks
"Bags & Backpacks": {
    "Persuasive": [
        "Carry with confidence using {keyword} — built for every journey.",
        "Upgrade your style and storage with {keyword}."
    ],
    "Casual": [
        "Pack it all with {keyword} — simple, sturdy, and reliable.",
        "Everyday adventures made easy with {keyword}."
    ],
    "Luxury": [
        "Experience premium craftsmanship with {keyword}, designed for elegance.",
        "Timeless style meets durability — {keyword} delivers both."
    ],
    "Urgent": [
        "Hot drop: {keyword} — selling fast.",
        "Don’t wait — {keyword} is almost gone."
    ],
    "Tech-savvy": [
        "Smart design meets innovation — {keyword} is future‑ready gear.",
        "Engineered for convenience and style — {keyword} redefines carrying."
    ]
},

# 39. Outdoor Gear
"Outdoor Gear": {
    "Persuasive": [
        "Conquer the outdoors with {keyword} — built for adventure.",
        "Gear up for success with {keyword}, trusted by explorers."
    ],
    "Casual": [
        "Enjoy the outdoors with {keyword}.",
        "Adventure made simple with {keyword}."
    ],
    "Luxury": [
        "Experience premium adventure with {keyword}, crafted for explorers.",
        "Elite design meets rugged durability — {keyword} delivers."
    ],
    "Urgent": [
        "Don’t miss out — {keyword} is selling fast.",
        "Hot pick: {keyword} — limited stock available."
    ],
    "Tech-savvy": [
        "Smart adventure starts with {keyword}, engineered for performance.",
        "Innovation meets exploration — {keyword} redefines outdoor gear."
    ]
},
# 40. Home Decor
"Home Decor": {
    "Persuasive": [
        "Transform your space with {keyword} — style that inspires.",
        "Upgrade your home with {keyword}, crafted for beauty and comfort."
    ],
    "Casual": [
        "Make your house a home with {keyword}.",
        "Everyday style made simple with {keyword}."
    ],
    "Luxury": [
        "Experience timeless elegance with {keyword}, designed for distinction.",
        "Premium design meets comfort — {keyword} elevates your space."
    ],
    "Urgent": [
        "Hot trend: {keyword} — order before it’s gone.",
        "Don’t wait — {keyword} is in high demand."
    ],
    "Tech-savvy": [
        "Smart living starts with {keyword}, engineered for modern homes.",
        "Innovation meets design — {keyword} redefines home decor."
    ]
},
# 41. Travel Experiences
"Travel Experiences": {
    "Persuasive": [
        "Discover the world with {keyword} — memories that last a lifetime.",
        "Upgrade your journey with {keyword}, trusted by explorers everywhere."
    ],
    "Casual": [
        "Plan your next adventure with {keyword}.",
        "Everyday escapes made easy with {keyword}."
    ],
    "Luxury": [
        "Experience first‑class travel with {keyword}, crafted for elegance.",
        "Premium journeys begin with {keyword} — where comfort meets discovery."
    ],
    "Urgent": [
        "Hot deal: {keyword} — book before it’s gone.",
        "Don’t wait — {keyword} is filling fast."
    ],
    "Tech-savvy": [
        "Smart travel starts with {keyword}, engineered for convenience.",
        "Innovation meets adventure — {keyword} redefines exploration."
    ]
},

# 42. Educational Supplies
"Educational Supplies": {
    "Persuasive": [
        "Unlock learning with {keyword} — tools that inspire success.",
        "Boost knowledge and creativity with {keyword}."
    ],
    "Casual": [
        "Make studying easier with {keyword}.",
        "Everyday learning made fun with {keyword}."
    ],
    "Luxury": [
        "Premium learning starts with {keyword}, crafted for excellence.",
        "Experience top‑tier education tools with {keyword}."
    ],
    "Urgent": [
        "Back‑to‑school rush: {keyword} — order now.",
        "Don’t miss out — {keyword} is in high demand."
    ],
    "Tech-savvy": [
        "Smart learning begins with {keyword}, powered by innovation.",
        "Future‑ready education tools — {keyword} keeps you ahead."
    ]
},

# 43. Health & Fitness Equipment
"Health & Fitness Equipment": {
    "Persuasive": [
        "Achieve your goals with {keyword} — built for results.",
        "Transform your workouts with {keyword}, trusted by athletes."
    ],
    "Casual": [
        "Stay active with {keyword}.",
        "Everyday fitness made simple with {keyword}."
    ],
    "Luxury": [
        "Experience elite performance with {keyword}, crafted for champions.",
        "Premium design meets endurance — {keyword} delivers."
    ],
    "Urgent": [
        "Hot pick: {keyword} — limited stock available.",
        "Don’t wait — {keyword} is selling fast."
    ],
    "Tech-savvy": [
        "Smart workouts start with {keyword}, engineered for precision.",
        "Innovation meets strength — {keyword} redefines fitness."
    ]
},

# 44. Green & Eco-Friendly
"Green & Eco-Friendly": {
    "Persuasive": [
        "Go green with {keyword} — better for you and the planet.",
        "Sustainable living starts with {keyword}, trusted worldwide."
    ],
    "Casual": [
        "Make eco‑friendly choices with {keyword}.",
        "Everyday sustainability made simple with {keyword}."
    ],
    "Luxury": [
        "Experience eco‑luxury with {keyword}, crafted for conscious living.",
        "Premium sustainability meets style — {keyword} delivers both."
    ],
    "Urgent": [
        "Act now — {keyword} is in high demand.",
        "Limited stock of {keyword} — go green today."
    ],
    "Tech-savvy": [
        "Smart sustainability starts with {keyword}, engineered for impact.",
        "Innovation meets eco‑living — {keyword} redefines green choices."
    ]
},

# 45. Luxury Goods
"Luxury Goods": {
    "Persuasive": [
        "Indulge in {keyword} — elegance that speaks volumes.",
        "Upgrade your lifestyle with {keyword}, crafted for distinction."
    ],
    "Casual": [
        "Add a touch of class with {keyword}.",
        "Everyday elegance made simple with {keyword}."
    ],
    "Luxury": [
        "Experience timeless prestige with {keyword}, designed for connoisseurs.",
        "Premium craftsmanship meets exclusivity — {keyword} is luxury redefined."
    ],
    "Urgent": [
        "Exclusive drop: {keyword} — secure yours today.",
        "Don’t wait — {keyword} is almost gone."
    ],
    "Tech-savvy": [
        "Smart luxury starts with {keyword}, engineered for modern living.",
        "Innovation meets elegance — {keyword} is future‑ready prestige."
    ]
},
# 46. Collectibles & Memorabilia
"Collectibles & Memorabilia": {
    "Persuasive": [
        "Own a piece of history with {keyword} — timeless and unique.",
        "Add lasting value to your collection with {keyword}."
    ],
    "Casual": [
        "Show off your passion with {keyword}.",
        "Everyday collecting made fun with {keyword}."
    ],
    "Luxury": [
        "Experience prestige with {keyword}, crafted for true collectors.",
        "Premium artistry meets rarity — {keyword} is unforgettable."
    ],
    "Urgent": [
        "Rare find: {keyword} — secure it before it’s gone.",
        "Don’t miss your chance to own {keyword} today."
    ],
    "Tech-savvy": [
        "Smart collecting starts with {keyword}, blending tradition and tech.",
        "Innovation meets nostalgia — {keyword} redefines memorabilia."
    ]
},

# 47. DIY & Crafts
"DIY & Crafts": {
    "Persuasive": [
        "Bring your ideas to life with {keyword} — tools that inspire.",
        "Create with confidence using {keyword}, trusted by makers."
    ],
    "Casual": [
        "Make every project fun with {keyword}.",
        "Everyday creativity starts with {keyword}."
    ],
    "Luxury": [
        "Elevate your craft with {keyword}, crafted for perfection.",
        "Premium quality meets artistry — {keyword} inspires brilliance."
    ],
    "Urgent": [
        "Hot pick for creators: {keyword} — get yours today.",
        "Don’t wait — {keyword} is selling fast."
    ],
    "Tech-savvy": [
        "Smart creativity starts with {keyword}, engineered for precision.",
        "Innovation meets artistry — {keyword} redefines DIY."
    ]
},

# 48. Luxury Travel
"Luxury Travel": {
    "Persuasive": [
        "Indulge in world‑class journeys with {keyword}.",
        "Upgrade your adventures with {keyword}, crafted for elegance."
    ],
    "Casual": [
        "Travel in style with {keyword}.",
        "Everyday escapes made extraordinary with {keyword}."
    ],
    "Luxury": [
        "Experience first‑class comfort with {keyword}, designed for distinction.",
        "Premium journeys begin with {keyword} — where elegance meets adventure."
    ],
    "Urgent": [
        "Exclusive trip: {keyword} — book before it’s gone.",
        "Don’t wait — {keyword} is filling fast."
    ],
    "Tech-savvy": [
        "Smart travel starts with {keyword}, engineered for modern explorers.",
        "Innovation meets luxury — {keyword} redefines journeys."
    ]
},

# 49. Digital Products
"Digital Products": {
    "Persuasive": [
        "Unlock instant access with {keyword} — convenience at your fingertips.",
        "Upgrade your digital life with {keyword}, trusted worldwide."
    ],
    "Casual": [
        "Download and enjoy {keyword} — quick, simple, and fun.",
        "Everyday convenience made easy with {keyword}."
    ],
    "Luxury": [
        "Experience premium digital content with {keyword}.",
        "Exclusive access begins with {keyword}, crafted for distinction."
    ],
    "Urgent": [
        "Hot release: {keyword} — download before it’s gone.",
        "Don’t wait — {keyword} is trending now."
    ],
    "Tech-savvy": [
        "Smart living starts with {keyword}, optimized for performance.",
        "Innovation meets convenience — {keyword} redefines digital."
    ]
},

# 50. Subscription Services
"Subscription Services": {
    "Persuasive": [
        "Enjoy endless value with {keyword} — convenience delivered monthly.",
        "Upgrade your lifestyle with {keyword}, trusted by thousands."
    ],
    "Casual": [
        "Sign up and enjoy {keyword} — simple and stress‑free.",
        "Everyday life made easier with {keyword}."
    ],
    "Luxury": [
        "Experience premium perks with {keyword}, crafted for distinction.",
        "Exclusive benefits await with {keyword}."
    ],
    "Urgent": [
        "Limited offer: {keyword} — subscribe today.",
        "Don’t wait — {keyword} is filling fast."
    ],
    "Tech-savvy": [
        "Smart subscriptions start with {keyword}, engineered for convenience.",
        "Innovation meets lifestyle — {keyword} redefines membership."
    ]
},
# 51. Home Improvement
"Home Improvement": {
    "Persuasive": [
        "Upgrade your space with {keyword} — built for lasting impact.",
        "Transform your home with {keyword}, trusted by DIYers and pros alike."
    ],
    "Casual": [
        "Fix it fast with {keyword}.",
        "Everyday projects made simple with {keyword}."
    ],
    "Luxury": [
        "Experience premium craftsmanship with {keyword}, designed for distinction.",
        "Elevate your home with {keyword} — where quality meets style."
    ],
    "Urgent": [
        "Hot pick: {keyword} — limited stock available.",
        "Don’t wait — {keyword} is selling fast."
    ],
    "Tech-savvy": [
        "Smart upgrades start with {keyword}, engineered for efficiency.",
        "Innovation meets durability — {keyword} redefines home improvement."
    ]
},

# 52. Safety & Security
"Safety & Security": {
    "Persuasive": [
        "Protect what matters most with {keyword}.",
        "Peace of mind starts with {keyword}, trusted worldwide."
    ],
    "Casual": [
        "Stay safe and secure with {keyword}.",
        "Everyday protection made easy with {keyword}."
    ],
    "Luxury": [
        "Experience premium protection with {keyword}, crafted for reliability.",
        "Elite security meets modern design — {keyword} delivers both."
    ],
    "Urgent": [
        "Act now — {keyword} is in high demand.",
        "Don’t wait — safeguard your home with {keyword} today."
    ],
    "Tech-savvy": [
        "Smart security starts with {keyword}, engineered for innovation.",
        "Future‑ready protection — {keyword} redefines safety."
    ]
},

# 53. Automotive Care
"Automotive Care": {
    "Persuasive": [
        "Keep your ride in top shape with {keyword}.",
        "Trusted by drivers everywhere — {keyword} delivers performance."
    ],
    "Casual": [
        "Make car care easy with {keyword}.",
        "Everyday maintenance starts with {keyword}."
    ],
    "Luxury": [
        "Experience premium auto care with {keyword}, crafted for distinction.",
        "Elite performance meets shine — {keyword} redefines car care."
    ],
    "Urgent": [
        "Running low? Restock {keyword} before it’s gone.",
        "Don’t wait — {keyword} is in high demand."
    ],
    "Tech-savvy": [
        "Smart maintenance starts with {keyword}, engineered for precision.",
        "Innovation meets performance — {keyword} is car care reimagined."
    ]
},

# 54. Entertainment & Events
"Entertainment & Events": {
    "Persuasive": [
        "Make every moment unforgettable with {keyword}.",
        "Upgrade your celebrations with {keyword}, crafted for joy."
    ],
    "Casual": [
        "Have fun with {keyword} — simple, exciting, and memorable.",
        "Everyday entertainment made better with {keyword}."
    ],
    "Luxury": [
        "Experience premium events with {keyword}, designed for distinction.",
        "Elite entertainment begins with {keyword}."
    ],
    "Urgent": [
        "Hot ticket: {keyword} — secure yours today.",
        "Don’t wait — {keyword} is almost sold out."
    ],
    "Tech-savvy": [
        "Smart entertainment starts with {keyword}, powered by innovation.",
        "Innovation meets excitement — {keyword} redefines events."
    ]
}}

# --- Keyword extraction ---
def extract_main_keyword(text):
    """Extract a main keyword candidate from the listing text."""
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9]+\b", text)
    keywords = [w for w in words if len(w) > 3]
    return keywords[0] if keywords else "your product"

def extract_keywords(text):
    """Extract all unique keywords from the listing text."""
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9]+\b", text)
    keywords = sorted(set([w for w in words if len(w) > 3]), key=str.lower)
    return ", ".join(keywords) if keywords else "No keywords found."

# --- Listing Optimizer (Unified with DEFAULT_TEMPLATE + REWRITE_TEMPLATES) ---

# --- Optimizer using templates ---
def optimize_listing(text, tone, category, mode="Fast"):
    words = text.split()
    if len(words) > 1 and words[0].lower() == words[1].lower():
        text = " ".join(words[1:])

    prefix = "⚡ Quick boost:" if mode.startswith("Fast") else "🌟 Premium rewrite:"

    templates = None
    if category in REWRITE_TEMPLATES and tone in REWRITE_TEMPLATES[category]:
        templates = REWRITE_TEMPLATES[category][tone]
    elif tone in DEFAULT_TEMPLATE:
        templates = DEFAULT_TEMPLATE[tone]

    keyword = extract_main_keyword(text)

    if templates and len(templates) >= 2:
        headline = templates[0].format(keyword=keyword)
        tagline = templates[1].format(keyword=keyword)
        return f"{prefix} {headline}\n\n{tagline}"
    else:
        return f"{prefix} {text}\n\nSmart add‑ons for everyday performance."

def generate_all_tones(text, category, mode="Fast"):
    tones = ["Persuasive", "Casual", "Luxury", "Urgent", "Tech-savvy"]
    return {tone: optimize_listing(text, tone, category, mode) for tone in tones}

# --- Keyword-based category detection with keyword logging ---
CATEGORY_KEYWORDS = {
    "Fashion & Apparel": [
        "shirt", "tshirt", "jeans", "dress", "kurta", "saree", "hoodie", "jacket",
        "sneakers", "shoes", "sandals", "heels", "trousers", "shorts", "skirt",
        "suit", "blazer", "scarf", "hat", "cap", "belt", "socks", "gloves"
    ],
    "Electronics": [
        "phone", "smartphone", "mobile", "laptop", "tablet", "desktop", "pc",
        "camera", "dslr", "earbuds", "headphones", "charger", "powerbank",
        "monitor", "keyboard", "mouse", "printer", "speaker", "tv", "smartwatch"
    ],
    "Home & Kitchen": [
        "pan", "pot", "cookware", "utensil", "knife", "spoon", "fork", "plate",
        "bowl", "mug", "cup", "glass", "oven", "microwave", "toaster", "blender",
        "mixer", "fridge", "vacuum", "sofa", "chair", "table", "bed", "pillow",
        "mattress", "curtain", "rug", "lamp", "fan"
    ],
    "Toys & Games": [
        "toy", "lego", "puzzle", "boardgame", "doll", "car", "truck", "train",
        "action figure", "playset", "ball", "kite", "drone", "rc car", "game",
        "console", "controller", "ps5", "xbox", "nintendo"
    ],
    "Beauty & Personal Care": [
        "cream", "gel", "serum", "shampoo", "conditioner", "soap", "facewash",
        "lipstick", "eyeliner", "mascara", "foundation", "perfume", "deodorant",
        "lotion", "oil", "sunscreen", "toothpaste", "toothbrush", "razor",
        "trimmer", "makeup", "cosmetic"
    ],
    "Books & Stationery": [
        "book", "novel", "magazine", "comic", "journal", "diary", "notebook",
        "pen", "pencil", "marker", "highlighter", "eraser", "sharpener",
        "ruler", "sketchbook", "planner", "calendar", "folder", "binder"
    ],
    "Sports & Outdoors": [
        "football", "soccer", "basketball", "cricket", "bat", "ball", "racket",
        "tennis", "badminton", "golf", "yoga", "mat", "dumbbell", "treadmill",
        "bicycle", "helmet", "tent", "backpack", "sleeping bag", "hiking"
    ],
    "Automotive": [
        "car", "bike", "motorcycle", "scooter", "helmet", "tyre", "tire",
        "engine", "brake", "seat cover", "floor mat", "wiper", "mirror",
        "headlight", "taillight", "battery", "charger", "gps", "dashcam"
    ],
    "Grocery & Gourmet": [
        "rice", "flour", "sugar", "salt", "oil", "spice", "masala", "tea",
        "coffee", "snack", "chips", "chocolate", "biscuit", "cookie", "juice",
        "soda", "cereal", "pasta", "sauce", "honey", "jam", "pickle"
    ],
    "Health & Wellness": [
        "vitamin", "supplement", "protein", "powder", "capsule", "tablet",
        "medicine", "bandage", "sanitizer", "mask", "gloves", "thermometer",
        "bp monitor", "weighing scale", "yoga mat", "fitness tracker"
    ],
    "Jewelry & Accessories": [
        "ring", "necklace", "bracelet", "earring", "bangle", "chain", "watch",
        "sunglasses", "wallet", "handbag", "backpack", "clutch", "tie", "cufflink"
    ],
    "Pet Supplies": [
        "dog", "cat", "leash", "collar", "kennel", "cage", "aquarium", "fish food",
        "bird food", "pet bed", "scratcher", "litter", "treats", "toys"
    ],
    "Baby Products": [
        "diaper", "stroller", "crib", "bottle", "pacifier", "rattle", "onesie",
        "baby food", "formula", "wipes", "car seat", "high chair"
    ]
}

def detect_category(text, mode="Fast"):
    text_lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for word in keywords:
            if word in text_lower:
                # Log which keyword triggered the match
                st.write(f"🔍 Matched keyword: '{word}' → Category: {category}")
                return category
    return "General"

# --- Optimization Trigger ---
if st.button("✨ Optimize Listings", key="optimize_listings_button_final"):
    listings = [line.strip() for line in input_text.split("\n") if line.strip()]

    if not listings:
        st.warning("⚠️ Please enter at least one listing.")

    elif len(listings) == 1:
        listing = listings[0]
        with st.spinner("✨ Optimizing your listing..."):
            category = detect_category(listing, mode)
            optimized = optimize_listing(listing, tone, category, mode)

        st.success("✅ Optimization complete")
        st.markdown(f"**📦 Detected Category:** {category}")
        st.text_area("Optimized listing", value=optimized, height=220, key="single_output_final")
        st.download_button(
            label="⬇️ Download",
            data=optimized,
            file_name="listing.txt",
            mime="text/plain",
            key="single_dl_final"
        )

    else:
        st.success(f"✅ Optimizing {len(listings)} listings...")
        progress = st.progress(0)
        status = st.empty()
        all_outputs = []

        for i, listing in enumerate(listings, start=1):
            status.text(f"Processing listing {i} of {len(listings)}...")
            category = detect_category(listing, mode)
            tone_variants = generate_all_tones(listing, category, mode)
            keywords = extract_keywords(
                tone_variants.get("Persuasive", next(iter(tone_variants.values())))
            )

            st.markdown(f"## 🛍️ Listing {i}")
            st.markdown(f"**📦 Detected Category:** {category}")

            tabs = st.tabs(list(tone_variants.keys()))
            for j, tone_name in enumerate(tone_variants):
                with tabs[j]:
                    st.markdown(f"### 🎨 {tone_name} Tone")
                    st.text_area(
                        f"{tone_name} Output",
                        tone_variants[tone_name],
                        height=180,
                        key=f"bulk_text_{i}_{j}"
                    )
                    st.download_button(
                        label="⬇️ Download",
                        data=tone_variants[tone_name],
                        file_name=f"listing{i}_{tone_name.lower()}.txt",
                        mime="text/plain",
                        key=f"bulk_dl_{i}_{j}"
                    )

            st.markdown(f"**🔑 Suggested Keywords:**\n\n{keywords}")
            st.download_button(
                label="⬇️ Download Keywords",
                data=keywords,
                file_name=f"listing{i}_keywords.txt",
                key=f"keyword_dl_{i}"
            )

            all_outputs.append(f"Listing {i} ({category}):\n{tone_variants}\nKeywords: {keywords}\n")
            progress.progress(i / len(listings))

        final_output = "\n\n".join(all_outputs)
        st.download_button(
            label="⬇️ Download All Listings",
            data=final_output,
            file_name="bulk_listings.txt",
            mime="text/plain",
            key="bulk_dl_final"
        )
            # --- Notify Me form (engagement) ---
st.markdown("### 🔔 Stay in the Loop")
notify_input = st.text_input(
    "📧 Want early access to new features?",
    placeholder="Enter your email",
    key="notify_input"
)

if st.button("Notify Me", key="notify_btn"):
    if notify_input.strip():
        email = notify_input.strip()

        # --- Save to session state ---
        if "waitlist" not in st.session_state:
            st.session_state["waitlist"] = []
        st.session_state["waitlist"].append(email)

        # --- Persist to CSV file ---
        try:
            file_exists = os.path.isfile("waitlist.csv")
            with open("waitlist.csv", "a", newline="") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["email"])
                writer.writerow([email])
            st.success("✅ You're on the waitlist! We'll keep you posted.")
        except Exception as e:
            st.error(f"⚠️ Could not save email: {e}")
    else:
        st.warning("⚠️ Please enter a valid email address.")

# --- Footer (always last) ---
st.markdown("---", unsafe_allow_html=True)
st.markdown(
    """
    <div style="
        text-align: center;
        font-size: 14px;
        color: #555555;
        line-height: 1.6;
        margin-top: 20px;
    ">
        🛍️ <b>SellSpark</b> — AI‑powered e‑commerce listing optimizer<br>
        Built with ❤️ by <b>Syed Mohammed Muzzammil</b><br>
        <a href="https://www.linkedin.com/in/syed-mohammed-muzzammil" target="_blank" style="color: #0A66C2; text-decoration: none;">
            Connect on LinkedIn
        </a><br>
        Powered by <b>Streamlit</b> & <b>Hugging Face</b><br>
        © 2025 SellSpark. All rights reserved.
    </div>
    """,
    unsafe_allow_html=True
)
