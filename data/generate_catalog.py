"""Generate a small, deliberately MESSY product catalog CSV.

Why generate instead of downloading? So the project runs offline with zero setup.
The mess is on purpose: real e-commerce exports look like this, and the cleaning
step in `spf/ingest.py` has to deal with it.

Mess we inject:
  * prices in many formats: "₹1,299", "Rs. 1299", "1299.00", "INR 1299", blank
  * HTML tags and extra whitespace in descriptions
  * specs stored as one ugly string: {"key"=>"value", ...}  (Flipkart-style)
  * category stored as a breadcrumb: "Home >> Kitchen >> Drinkware"
  * duplicate rows and rows with a missing name
  * random UPPER/lower case in names

Run:  python data/generate_catalog.py   ->  writes data/products_raw.csv
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

random.seed(42)

# (type_id, category breadcrumb, product noun, description, specs)
# Descriptions are written the way a seller would write them, NOT the way a
# shopper would search. That gap is exactly what semantic search is for.
PRODUCT_TYPES = [
    # ---------------- Electronics ----------------
    ("wireless_earbuds", "Electronics >> Audio >> Headphones", "True Wireless Earbuds",
     "Bluetooth 5.3 in-ear buds with charging case, 30 hour total playback, touch controls and IPX5 sweat resistance.",
     {"Connectivity": "Bluetooth 5.3", "Battery": "30 hours", "Water Resistance": "IPX5"}),
    ("anc_headphones", "Electronics >> Audio >> Headphones", "Over-Ear ANC Headphones",
     "Active noise cancelling over-ear headphones with plush memory foam cushions. Blocks engine rumble and office chatter. 40 hour battery.",
     {"Type": "Over-ear", "ANC": "Yes", "Battery": "40 hours"}),
    ("bt_speaker", "Electronics >> Audio >> Speakers", "Portable Bluetooth Speaker",
     "Compact rugged speaker with deep bass, IPX7 waterproof rating, floats in water, 12 hour playtime.",
     {"Output": "10W", "Water Resistance": "IPX7", "Battery": "12 hours"}),
    ("power_bank", "Electronics >> Mobile Accessories >> Power Banks", "20000mAh Power Bank",
     "High capacity portable charger with 22.5W fast charging, two USB-A ports and one USB-C PD port. Charges a phone four times.",
     {"Capacity": "20000mAh", "Output": "22.5W", "Ports": "3"}),
    ("smartwatch", "Electronics >> Wearables >> Smart Watches", "Fitness Smartwatch",
     "AMOLED smartwatch with heart rate, SpO2, sleep tracking, 100 sports modes and 10 day battery life.",
     {"Display": "1.43 inch AMOLED", "Battery": "10 days", "Sensors": "HR, SpO2"}),
    ("webcam", "Electronics >> Computer Accessories >> Webcams", "1080p HD Webcam",
     "Full HD USB camera with dual noise-reducing microphones and auto light correction, plug and play on Windows and Mac.",
     {"Resolution": "1080p", "Mic": "Dual", "Interface": "USB"}),
    ("mech_keyboard", "Electronics >> Computer Accessories >> Keyboards", "Mechanical Keyboard",
     "Tenkeyless mechanical keyboard with hot-swappable tactile brown switches and RGB backlight.",
     {"Switch": "Brown", "Layout": "TKL", "Backlight": "RGB"}),
    ("ergo_mouse", "Electronics >> Computer Accessories >> Mice", "Vertical Ergonomic Mouse",
     "Vertical handshake grip mouse that reduces wrist strain and forearm twisting during long work sessions. Silent clicks, 2.4G wireless.",
     {"Grip": "Vertical", "Connectivity": "2.4G Wireless", "DPI": "800-2400"}),
    ("laptop_stand", "Electronics >> Computer Accessories >> Stands", "Aluminium Laptop Stand",
     "Adjustable aluminium riser that lifts the screen to eye level, foldable, fits 10 to 17 inch notebooks, improves posture.",
     {"Material": "Aluminium", "Adjustable": "Yes", "Fits": "10-17 inch"}),
    ("usb_hub", "Electronics >> Computer Accessories >> Hubs", "7-in-1 USB-C Hub",
     "USB-C dongle with 4K HDMI out, SD and microSD card reader, two USB 3.0 ports and 100W pass-through charging.",
     {"Ports": "7", "HDMI": "4K", "PD": "100W"}),
    ("ebook_reader", "Electronics >> Tablets >> E-Readers", "6 inch E-Ink Reader",
     "Glare-free e-paper display that reads like real paper even in direct sunlight, warm front light, weeks of battery, holds thousands of titles.",
     {"Display": "6 inch E-Ink", "Storage": "16GB", "Battery": "6 weeks"}),
    ("action_cam", "Electronics >> Cameras >> Action Cameras", "4K Action Camera",
     "Waterproof 4K60 action cam with electronic image stabilisation and helmet, bike and chest mounts included.",
     {"Resolution": "4K60", "Stabilisation": "EIS", "Waterproof": "10m with case"}),
    # ---------------- Kitchen ----------------
    ("insulated_tumbler", "Home >> Kitchen >> Drinkware", "Vacuum Insulated Tumbler",
     "Double-wall stainless steel travel mug with leakproof slide lid. Keeps beverages at temperature for up to 12 hours. Fits car cup holders.",
     {"Capacity": "500ml", "Material": "Stainless Steel", "Insulation": "Double wall vacuum"}),
    ("water_bottle", "Home >> Kitchen >> Drinkware", "Steel Water Bottle",
     "1 litre BPA-free stainless steel bottle, single wall, leakproof cap, dishwasher safe.",
     {"Capacity": "1L", "Material": "Stainless Steel", "BPA Free": "Yes"}),
    ("air_fryer", "Home >> Kitchen >> Appliances", "Digital Air Fryer",
     "4.5 litre hot air cooker that makes crispy fries and snacks using up to 90% less oil. Rapid air technology, 8 presets.",
     {"Capacity": "4.5L", "Power": "1500W", "Presets": "8"}),
    ("electric_kettle", "Home >> Kitchen >> Appliances", "Electric Kettle",
     "1.5L stainless steel kettle, boils water in under 4 minutes, auto shut-off and boil-dry protection.",
     {"Capacity": "1.5L", "Power": "1500W", "Auto Off": "Yes"}),
    ("blender", "Home >> Kitchen >> Appliances", "Personal Blender",
     "Single-serve blender with two to-go bottles for smoothies and protein shakes, 400W motor, blends ice.",
     {"Power": "400W", "Jars": "2 x 600ml", "Blade": "Stainless steel"}),
    ("chef_knife", "Home >> Kitchen >> Cutlery", "8 inch Chef Knife",
     "High-carbon German steel chef's knife with full tang and ergonomic handle for slicing, dicing and mincing.",
     {"Blade": "8 inch", "Steel": "High carbon", "Handle": "Pakkawood"}),
    ("nonstick_pan", "Home >> Kitchen >> Cookware", "Non-Stick Frying Pan",
     "28cm granite-coated frying pan, PFOA free, induction base, needs very little oil.",
     {"Size": "28cm", "Coating": "Granite", "Induction": "Yes"}),
    ("lunch_box", "Home >> Kitchen >> Storage", "Insulated Lunch Box",
     "Three-tier steel tiffin in an insulated carry bag that keeps your homemade meal warm till afternoon.",
     {"Containers": "3", "Material": "Stainless Steel", "Bag": "Insulated"}),
    ("coffee_grinder", "Home >> Kitchen >> Appliances", "Burr Coffee Grinder",
     "Conical burr grinder with 30 grind settings from espresso fine to French press coarse.",
     {"Burr": "Conical", "Settings": "30", "Hopper": "250g"}),
    ("french_press", "Home >> Kitchen >> Coffee & Tea", "French Press",
     "Borosilicate glass plunger brewer with 4-level stainless filter, makes 4 cups of rich full-bodied brew.",
     {"Capacity": "800ml", "Material": "Borosilicate glass", "Filter": "4-level"}),
    # ---------------- Fitness ----------------
    ("yoga_mat", "Sports >> Fitness >> Yoga", "Yoga Mat 6mm",
     "Non-slip TPE exercise mat, 6mm cushioning that protects knees and joints, with carry strap.",
     {"Thickness": "6mm", "Material": "TPE", "Size": "183 x 61 cm"}),
    ("dumbbells", "Sports >> Fitness >> Strength", "Adjustable Dumbbells",
     "Space-saving adjustable dumbbell set, 2.5 to 24 kg per hand with a quick dial selector. Replaces 15 pairs of weights.",
     {"Weight Range": "2.5-24 kg", "Adjustment": "Dial", "Pairs Replaced": "15"}),
    ("resistance_bands", "Sports >> Fitness >> Strength", "Resistance Band Set",
     "Set of 5 latex loop bands in different tension levels for home workouts, physiotherapy and stretching. Packs into a pouch.",
     {"Bands": "5", "Material": "Latex", "Levels": "X-light to X-heavy"}),
    ("foam_roller", "Sports >> Fitness >> Recovery", "High Density Foam Roller",
     "Textured foam roller for deep tissue massage and post-workout muscle recovery, relieves soreness and tight IT bands.",
     {"Length": "33cm", "Density": "High", "Surface": "Textured"}),
    ("running_shoes", "Sports >> Footwear >> Running", "Lightweight Running Shoes",
     "Breathable knit upper with responsive cushioned midsole for road running and marathon training.",
     {"Upper": "Knit mesh", "Drop": "8mm", "Use": "Road running"}),
    ("jump_rope", "Sports >> Fitness >> Cardio", "Speed Skipping Rope",
     "Adjustable steel cable rope with ball bearing handles for double unders and cardio conditioning.",
     {"Cable": "Steel", "Handles": "Aluminium", "Adjustable": "Yes"}),
    ("cycling_helmet", "Sports >> Cycling >> Safety", "Cycling Helmet",
     "Lightweight in-mould bike helmet with 18 vents, rear LED light and adjustable fit dial.",
     {"Vents": "18", "Light": "Rear LED", "Certification": "CE EN1078"}),
    ("pullup_bar", "Sports >> Fitness >> Strength", "Doorway Pull Up Bar",
     "No-screw doorframe chin-up bar for upper body strength training at home, holds up to 130 kg.",
     {"Max Load": "130 kg", "Install": "No screws", "Grips": "Foam"}),
    # ---------------- Home ----------------
    ("blackout_curtains", "Home >> Furnishing >> Curtains", "Blackout Curtains",
     "Thermal insulated curtains that block 99% of sunlight and street light, so the room stays dark for daytime naps and night-shift sleep.",
     {"Light Block": "99%", "Size": "7 ft", "Pieces": "2"}),
    ("led_desk_lamp", "Home >> Lighting >> Lamps", "LED Desk Lamp",
     "Flicker-free eye-care LED lamp with 5 colour temperatures, stepless dimming and a USB charging port.",
     {"Modes": "5", "Dimming": "Stepless", "USB": "Yes"}),
    ("air_purifier", "Home >> Appliances >> Air Purifiers", "HEPA Air Purifier",
     "True HEPA H13 purifier that captures 99.97% of dust, pollen, smoke and PM2.5. Ideal for allergy sufferers. Covers 350 sq ft.",
     {"Filter": "HEPA H13", "Coverage": "350 sq ft", "CADR": "220 m3/h"}),
    ("robot_vacuum", "Home >> Appliances >> Cleaning", "Robot Vacuum Cleaner",
     "Self-charging robotic vacuum with app control, mops and sweeps hard floors and carpets on a schedule.",
     {"Suction": "2700Pa", "Mop": "Yes", "Runtime": "120 min"}),
    ("memory_pillow", "Home >> Bedding >> Pillows", "Memory Foam Pillow",
     "Contoured cervical pillow that supports neck alignment for side and back sleepers. Helps with stiff neck in the morning.",
     {"Material": "Memory foam", "Shape": "Contour", "Cover": "Removable"}),
    ("weighted_blanket", "Home >> Bedding >> Blankets", "Weighted Blanket 7kg",
     "Glass-bead weighted blanket that applies gentle even pressure to calm the nervous system and improve rest.",
     {"Weight": "7kg", "Filling": "Glass beads", "Size": "Queen"}),
    ("smart_plug", "Home >> Smart Home >> Plugs", "Wi-Fi Smart Plug",
     "Control any appliance from your phone or with voice assistants, set schedules and timers, energy monitoring.",
     {"Connectivity": "Wi-Fi 2.4GHz", "Max Load": "16A", "Voice": "Alexa, Google"}),
    ("indoor_plant_pot", "Home >> Garden >> Planters", "Self-Watering Planter",
     "Ceramic planter with a hidden water reservoir that waters your houseplants for up to two weeks.",
     {"Material": "Ceramic", "Reservoir": "Yes", "Diameter": "18cm"}),
    ("mosquito_bat", "Home >> Pest Control >> Electric", "Rechargeable Mosquito Racket",
     "Electric fly swatter bat with LED torch, kills insects instantly, USB rechargeable.",
     {"Charging": "USB", "Torch": "LED", "Mesh": "3 layer"}),
    # ---------------- Fashion / Bags ----------------
    ("laptop_backpack", "Fashion >> Bags >> Backpacks", "Anti-Theft Laptop Backpack",
     "Water-repellent backpack with hidden zipper, padded 15.6 inch laptop sleeve and external USB charging port.",
     {"Laptop": "15.6 inch", "Capacity": "28L", "Anti-theft": "Yes"}),
    ("rain_jacket", "Fashion >> Men >> Jackets", "Packable Rain Jacket",
     "Lightweight waterproof windcheater with sealed seams and hood that folds into its own pocket.",
     {"Waterproof": "5000mm", "Hood": "Yes", "Packable": "Yes"}),
    ("sunglasses", "Fashion >> Accessories >> Eyewear", "Polarized Sunglasses",
     "UV400 polarized shades that cut glare from roads and water, lightweight TR90 frame.",
     {"Lens": "Polarized", "UV": "UV400", "Frame": "TR90"}),
    ("wallet", "Fashion >> Accessories >> Wallets", "RFID Blocking Leather Wallet",
     "Slim genuine leather bifold that blocks contactless card skimming, 8 card slots.",
     {"Material": "Genuine leather", "RFID": "Yes", "Slots": "8"}),
    ("thermal_wear", "Fashion >> Men >> Innerwear", "Thermal Innerwear Set",
     "Fleece-lined base layer top and bottom that traps body heat in freezing winters.",
     {"Material": "Fleece-lined", "Pieces": "2", "Season": "Winter"}),
    ("trekking_shoes", "Sports >> Footwear >> Hiking", "Waterproof Trekking Shoes",
     "Ankle-high hiking boots with grippy lugged outsole and waterproof membrane for mountain trails.",
     {"Height": "Mid", "Waterproof": "Yes", "Outsole": "Rubber lug"}),
    # ---------------- Outdoor / Travel ----------------
    ("camping_tent", "Sports >> Outdoor >> Camping", "4 Person Camping Tent",
     "Dome tent for four with rainfly, sets up in 10 minutes, carry bag included.",
     {"Capacity": "4 person", "Rainfly": "Yes", "Setup": "10 min"}),
    ("sleeping_bag", "Sports >> Outdoor >> Camping", "Sleeping Bag 0C",
     "Mummy sleeping bag rated to 0 degrees C, compresses small for backpacking.",
     {"Comfort": "0C", "Shape": "Mummy", "Weight": "1.4kg"}),
    ("headlamp", "Sports >> Outdoor >> Lighting", "LED Headlamp",
     "Rechargeable head torch with 300 lumens, red night mode and adjustable strap, hands-free light.",
     {"Lumens": "300", "Charging": "USB-C", "Modes": "5"}),
    ("neck_pillow", "Travel >> Accessories >> Pillows", "Travel Neck Pillow",
     "U-shaped memory foam pillow that stops your head from dropping on long flights and bus rides.",
     {"Material": "Memory foam", "Shape": "U", "Cover": "Washable"}),
    ("luggage_scale", "Travel >> Accessories >> Gadgets", "Digital Luggage Scale",
     "Handheld hanging scale that weighs suitcases up to 50 kg so you avoid excess baggage fees at the airport.",
     {"Max": "50 kg", "Display": "LCD", "Battery": "CR2032"}),
    ("travel_adapter", "Travel >> Accessories >> Adapters", "Universal Travel Adapter",
     "All-in-one plug converter for 150+ countries with 4 USB ports.",
     {"Countries": "150+", "USB": "4", "Fuse": "Yes"}),
    # ---------------- Beauty / Personal care ----------------
    ("hair_dryer", "Beauty >> Hair Care >> Dryers", "Ionic Hair Dryer",
     "1800W ionic blow dryer with concentrator nozzle, reduces frizz, 3 heat settings and cool shot.",
     {"Power": "1800W", "Ionic": "Yes", "Settings": "3"}),
    ("electric_trimmer", "Beauty >> Men's Grooming >> Trimmers", "Beard Trimmer",
     "Cordless trimmer with 20 length settings, 90 minute runtime, washable stainless blades.",
     {"Lengths": "20", "Runtime": "90 min", "Washable": "Yes"}),
    ("sunscreen", "Beauty >> Skin Care >> Sun Care", "SPF 50 Sunscreen",
     "Broad spectrum PA++++ gel sunscreen, non-greasy, no white cast, suitable for oily skin.",
     {"SPF": "50", "PA": "++++", "Texture": "Gel"}),
    ("electric_toothbrush", "Beauty >> Oral Care >> Toothbrushes", "Sonic Electric Toothbrush",
     "Rechargeable sonic toothbrush with 2 minute smart timer and 3 cleaning modes for whiter teeth and healthier gums.",
     {"Modes": "3", "Timer": "2 min", "Battery": "30 days"}),
    # ---------------- Books / Kids / Office ----------------
    ("python_book", "Books >> Computers >> Programming", "Python Crash Course Book",
     "Beginner friendly hands-on introduction to programming, covers basics then builds three projects.",
     {"Pages": "544", "Level": "Beginner", "Format": "Paperback"}),
    ("kids_building_blocks", "Toys >> Construction >> Blocks", "Building Blocks Set",
     "500 piece interlocking brick set that builds creativity and fine motor skills for kids aged 6+.",
     {"Pieces": "500", "Age": "6+", "Material": "ABS"}),
    ("board_game", "Toys >> Games >> Board Games", "Strategy Board Game",
     "Trading and settlement strategy game for 3 to 4 players, perfect for family game night.",
     {"Players": "3-4", "Age": "10+", "Time": "60 min"}),
    ("office_chair", "Furniture >> Office >> Chairs", "Ergonomic Office Chair",
     "Mesh back chair with adjustable lumbar support, headrest and 3D armrests for long hours at the desk.",
     {"Back": "Mesh", "Lumbar": "Adjustable", "Armrest": "3D"}),
    ("standing_desk", "Furniture >> Office >> Desks", "Electric Standing Desk",
     "Motorised height adjustable sit-stand desk with memory presets, switch between sitting and standing.",
     {"Height": "72-118 cm", "Motor": "Single", "Presets": "4"}),
    ("noise_machine", "Home >> Bedding >> Sleep Aids", "White Noise Machine",
     "Sound machine with 30 soothing sounds like rain and fan to mask snoring and traffic so you fall asleep faster.",
     {"Sounds": "30", "Timer": "Yes", "Power": "USB"}),
]

BRANDS = {
    "Electronics": ["Voltix", "Zentra", "Nimbus", "Kairo"],
    "Home": ["Hearthly", "Casa Nova", "Urbanest", "Kitchino"],
    "Sports": ["StrideX", "Peakform", "Trailblaze", "Fitora"],
    "Fashion": ["Urban Trail", "Northline", "Mavro"],
    "Travel": ["Jetsetr", "Roamly"],
    "Beauty": ["Glowra", "Sleekr"],
    "Books": ["Pageturn Press"],
    "Toys": ["Brickly", "Playwise"],
    "Furniture": ["Sitwell", "Deskora"],
}

BASE_PRICE = {  # rough INR price per type
    "wireless_earbuds": 1999, "anc_headphones": 8999, "bt_speaker": 2499, "power_bank": 1499,
    "smartwatch": 3499, "webcam": 1999, "mech_keyboard": 3999, "ergo_mouse": 1299,
    "laptop_stand": 1499, "usb_hub": 2299, "ebook_reader": 9999, "action_cam": 12999,
    "insulated_tumbler": 899, "water_bottle": 599, "air_fryer": 5499, "electric_kettle": 1199,
    "blender": 2199, "chef_knife": 1799, "nonstick_pan": 1399, "lunch_box": 999,
    "coffee_grinder": 3499, "french_press": 1099, "yoga_mat": 799, "dumbbells": 11999,
    "resistance_bands": 599, "foam_roller": 899, "running_shoes": 3999, "jump_rope": 499,
    "cycling_helmet": 1999, "pullup_bar": 1299, "blackout_curtains": 1499, "led_desk_lamp": 1299,
    "air_purifier": 8999, "robot_vacuum": 17999, "memory_pillow": 1499, "weighted_blanket": 3999,
    "smart_plug": 899, "indoor_plant_pot": 799, "mosquito_bat": 449, "laptop_backpack": 1899,
    "rain_jacket": 1999, "sunglasses": 1199, "wallet": 999, "thermal_wear": 899,
    "trekking_shoes": 3499, "camping_tent": 4999, "sleeping_bag": 2999, "headlamp": 799,
    "neck_pillow": 699, "luggage_scale": 449, "travel_adapter": 1199, "hair_dryer": 1999,
    "electric_trimmer": 1499, "sunscreen": 449, "electric_toothbrush": 2499, "python_book": 899,
    "kids_building_blocks": 1999, "board_game": 2499, "office_chair": 9999, "standing_desk": 24999,
    "noise_machine": 1999,
}

VARIANT_WORDS = ["", "Pro", "Lite", "Max", "Plus", "2.0", "Neo"]
MESSY_DESC_WRAPPERS = [
    "{d}",
    "<p>{d}</p>",
    "  {d}   ",
    "<b>Key Features:</b><br>{d}<br/>",
    "{d}\n\n\n",
    "<ul><li>{d}</li></ul>",
]


def messy_price(p: int) -> str:
    style = random.random()
    if style < 0.25:
        return f"₹{p:,}"
    if style < 0.45:
        return f"Rs. {p}"
    if style < 0.65:
        return f"{p}.00"
    if style < 0.8:
        return f"INR {p:,}"
    if style < 0.95:
        return str(p)
    return ""  # missing price


def messy_specs(specs: dict) -> str:
    # Flipkart-style blob: {"product_specification"=>[{"key"=>"X", "value"=>"Y"}, ...]}
    parts = [f'{{"key"=>"{k}", "value"=>"{v}"}}' for k, v in specs.items()]
    return '{"product_specification"=>[' + ", ".join(parts) + "]}"


def messy_case(s: str) -> str:
    r = random.random()
    if r < 0.1:
        return s.upper()
    if r < 0.2:
        return s.lower()
    return s


def main() -> None:
    rows = []
    pid = 1000
    for type_id, cat_path, noun, desc, specs in PRODUCT_TYPES:
        top = cat_path.split(" >> ")[0]
        brands = BRANDS[top]
        n_variants = random.choice([2, 3, 4])
        for _ in range(n_variants):
            brand = random.choice(brands)
            variant = random.choice(VARIANT_WORDS)
            name = f"{brand} {noun} {variant}".strip()
            mrp = int(BASE_PRICE[type_id] * random.uniform(0.75, 1.4))
            mrp = mrp - mrp % 10 + 9
            sale = int(mrp * random.uniform(0.6, 0.95))
            rating = round(random.uniform(3.2, 4.8), 1)
            pid += 1
            rows.append({
                "uniq_id": f"P{pid}",
                "product_name": messy_case(name),
                "product_category_tree": f'["{cat_path}"]',
                "retail_price": messy_price(mrp),
                "discounted_price": messy_price(sale),
                "brand": brand if random.random() > 0.08 else "",
                "description": random.choice(MESSY_DESC_WRAPPERS).format(d=desc),
                "product_specifications": messy_specs(specs),
                "product_rating": rating if random.random() > 0.15 else "No rating available",
                "type_id": type_id,  # ground truth label, used ONLY by the evaluation
            })

    # inject duplicates and broken rows
    for r in random.sample(rows, 8):
        rows.append(dict(r))
    for _ in range(3):
        broken = dict(random.choice(rows))
        broken["uniq_id"] = f"P{random.randint(9000, 9999)}"
        broken["product_name"] = ""
        rows.append(broken)
    random.shuffle(rows)

    out = Path(__file__).parent / "products_raw.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows ({len(PRODUCT_TYPES)} product types) -> {out}")


if __name__ == "__main__":
    main()
