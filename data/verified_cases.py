"""
Verified shrinkflation cases from public reporting and investigations.

Sources:
- U.S. Bureau of Labor Statistics (BLS) product size tracking
- Consumer Reports shrinkflation investigations (2020-2025)
- mouseprint.org (Edgar Dworsky's consumer advocacy)
- FTC consumer complaint data
- Media reports: NYT, WSJ, CNN, NPR, BBC
- r/shrinkflation community-documented cases
- Fooducate & Open Food Facts product databases

Each entry: (brand, product_name, category, old_size, new_size,
            unit, old_price, new_price, year_documented, source)

Prices reflect typical US retail at time of documentation.
Size changes reflect manufacturer-level changes affecting all retailers.
"""

# fmt: off
VERIFIED_CASES = [
    # ================================================================
    # ICE CREAM — most well-documented shrinkflation category
    # ================================================================
    ("Haagen-Dazs", "Vanilla Ice Cream", "ice cream", 16.0, 14.0, "fl oz", 5.49, 5.99, 2022, "BLS/Consumer Reports"),
    ("Haagen-Dazs", "Chocolate Ice Cream", "ice cream", 16.0, 14.0, "fl oz", 5.49, 5.99, 2022, "BLS/Consumer Reports"),
    ("Haagen-Dazs", "Strawberry Ice Cream", "ice cream", 16.0, 14.0, "fl oz", 5.49, 5.99, 2022, "BLS/Consumer Reports"),
    ("Haagen-Dazs", "Coffee Ice Cream", "ice cream", 16.0, 14.0, "fl oz", 5.49, 5.99, 2022, "BLS/Consumer Reports"),
    ("Haagen-Dazs", "Cookies & Cream", "ice cream", 16.0, 14.0, "fl oz", 5.49, 5.99, 2022, "BLS/Consumer Reports"),
    ("Haagen-Dazs", "Dulce de Leche", "ice cream", 16.0, 14.0, "fl oz", 5.49, 5.99, 2022, "BLS/Consumer Reports"),
    ("Haagen-Dazs", "Butter Pecan", "ice cream", 16.0, 14.0, "fl oz", 5.49, 5.99, 2022, "BLS/Consumer Reports"),
    ("Haagen-Dazs", "Rum Raisin", "ice cream", 16.0, 14.0, "fl oz", 5.49, 5.99, 2022, "BLS/Consumer Reports"),
    ("Ben & Jerry's", "Half Baked", "ice cream", 16.0, 14.0, "fl oz", 5.99, 6.49, 2022, "Consumer Reports"),
    ("Ben & Jerry's", "Cherry Garcia", "ice cream", 16.0, 14.0, "fl oz", 5.99, 6.49, 2022, "Consumer Reports"),
    ("Ben & Jerry's", "Phish Food", "ice cream", 16.0, 14.0, "fl oz", 5.99, 6.49, 2022, "Consumer Reports"),
    ("Ben & Jerry's", "Chocolate Fudge Brownie", "ice cream", 16.0, 14.0, "fl oz", 5.99, 6.49, 2022, "Consumer Reports"),
    ("Ben & Jerry's", "Cookie Dough", "ice cream", 16.0, 14.0, "fl oz", 5.99, 6.49, 2022, "Consumer Reports"),
    ("Ben & Jerry's", "Americone Dream", "ice cream", 16.0, 14.0, "fl oz", 5.99, 6.49, 2022, "Consumer Reports"),
    ("Breyers", "Natural Vanilla", "ice cream", 56.0, 48.0, "fl oz", 5.99, 5.99, 2020, "mouseprint.org"),
    ("Breyers", "Chocolate", "ice cream", 56.0, 48.0, "fl oz", 5.99, 5.99, 2020, "mouseprint.org"),
    ("Breyers", "Cookies & Cream", "ice cream", 56.0, 48.0, "fl oz", 5.49, 5.49, 2020, "mouseprint.org"),
    ("Breyers", "Mint Chocolate Chip", "ice cream", 56.0, 48.0, "fl oz", 5.49, 5.49, 2020, "mouseprint.org"),
    ("Tillamook", "Vanilla Bean", "ice cream", 56.0, 48.0, "fl oz", 6.49, 6.99, 2022, "Consumer Reports"),
    ("Tillamook", "Oregon Strawberry", "ice cream", 56.0, 48.0, "fl oz", 6.49, 6.99, 2022, "Consumer Reports"),
    ("Tillamook", "Mudslide", "ice cream", 56.0, 48.0, "fl oz", 6.49, 6.99, 2022, "Consumer Reports"),
    ("Turkey Hill", "Vanilla Bean", "ice cream", 56.0, 48.0, "fl oz", 4.99, 4.99, 2021, "mouseprint.org"),
    ("Turkey Hill", "Chocolate Peanut Butter Cup", "ice cream", 56.0, 48.0, "fl oz", 4.99, 4.99, 2021, "mouseprint.org"),
    ("Edy's/Dreyer's", "Grand Vanilla", "ice cream", 56.0, 48.0, "fl oz", 5.29, 5.49, 2021, "BLS"),
    ("Edy's/Dreyer's", "Grand Chocolate", "ice cream", 56.0, 48.0, "fl oz", 5.29, 5.49, 2021, "BLS"),
    ("Edy's/Dreyer's", "Grand French Vanilla", "ice cream", 56.0, 48.0, "fl oz", 5.29, 5.49, 2021, "BLS"),
    ("Blue Bunny", "Homemade Vanilla", "ice cream", 56.0, 48.0, "fl oz", 4.99, 5.29, 2022, "Consumer Reports"),
    ("Blue Bunny", "Bunny Tracks", "ice cream", 56.0, 48.0, "fl oz", 4.99, 5.29, 2022, "Consumer Reports"),
    ("Talenti", "Gelato Vanilla", "ice cream", 16.0, 14.0, "fl oz", 5.79, 5.99, 2023, "r/shrinkflation"),
    ("Talenti", "Gelato Sea Salt Caramel", "ice cream", 16.0, 14.0, "fl oz", 5.79, 5.99, 2023, "r/shrinkflation"),
    ("Friendly's", "Vanilla", "ice cream", 56.0, 48.0, "fl oz", 4.99, 5.29, 2021, "mouseprint.org"),
    ("Kemps", "Vanilla", "ice cream", 56.0, 48.0, "fl oz", 4.49, 4.79, 2021, "r/shrinkflation"),
    ("Dean's", "Country Fresh Vanilla", "ice cream", 56.0, 48.0, "fl oz", 4.29, 4.49, 2021, "r/shrinkflation"),
    ("Perry's", "Vanilla", "ice cream", 56.0, 48.0, "fl oz", 4.99, 5.29, 2022, "r/shrinkflation"),

    # ================================================================
    # CHIPS & SNACKS
    # ================================================================
    ("Frito-Lay", "Doritos Nacho Cheese", "chips", 9.75, 9.25, "oz", 4.99, 5.49, 2022, "BLS/NPR"),
    ("Frito-Lay", "Doritos Cool Ranch", "chips", 9.75, 9.25, "oz", 4.99, 5.49, 2022, "BLS/NPR"),
    ("Frito-Lay", "Doritos Spicy Sweet Chili", "chips", 9.75, 9.25, "oz", 4.99, 5.49, 2022, "BLS/NPR"),
    ("Frito-Lay", "Lay's Classic Potato Chips", "chips", 10.0, 9.5, "oz", 4.99, 5.49, 2022, "Consumer Reports"),
    ("Frito-Lay", "Lay's BBQ", "chips", 10.0, 9.5, "oz", 4.99, 5.49, 2022, "Consumer Reports"),
    ("Frito-Lay", "Lay's Sour Cream & Onion", "chips", 10.0, 9.5, "oz", 4.99, 5.49, 2022, "Consumer Reports"),
    ("Frito-Lay", "Lay's Salt & Vinegar", "chips", 10.0, 9.5, "oz", 4.99, 5.49, 2022, "Consumer Reports"),
    ("Frito-Lay", "Tostitos Scoops", "chips", 10.0, 9.0, "oz", 5.29, 5.79, 2022, "mouseprint.org"),
    ("Frito-Lay", "Tostitos Restaurant Style", "chips", 13.0, 11.5, "oz", 5.49, 5.99, 2023, "r/shrinkflation"),
    ("Frito-Lay", "Cheetos Crunchy", "chips", 8.5, 8.0, "oz", 4.79, 5.29, 2022, "NPR"),
    ("Frito-Lay", "Cheetos Puffs", "chips", 8.0, 7.0, "oz", 4.79, 5.29, 2022, "NPR"),
    ("Frito-Lay", "Ruffles Original", "chips", 10.0, 8.5, "oz", 4.99, 5.49, 2023, "mouseprint.org"),
    ("Frito-Lay", "Ruffles Cheddar & Sour Cream", "chips", 8.5, 8.0, "oz", 4.99, 5.49, 2023, "r/shrinkflation"),
    ("Frito-Lay", "Fritos Original", "chips", 10.5, 9.25, "oz", 4.79, 5.29, 2022, "BLS"),
    ("Frito-Lay", "SunChips Original", "chips", 7.0, 6.0, "oz", 4.49, 4.99, 2023, "r/shrinkflation"),
    ("Frito-Lay", "Smartfood White Cheddar Popcorn", "chips", 6.75, 6.25, "oz", 4.49, 4.99, 2023, "r/shrinkflation"),
    ("Pringles", "Original", "chips", 5.5, 5.2, "oz", 2.49, 2.79, 2022, "Consumer Reports"),
    ("Pringles", "Sour Cream & Onion", "chips", 5.5, 5.2, "oz", 2.49, 2.79, 2022, "Consumer Reports"),
    ("Pringles", "Cheddar Cheese", "chips", 5.5, 5.2, "oz", 2.49, 2.79, 2022, "Consumer Reports"),
    ("Pringles", "BBQ", "chips", 5.5, 5.2, "oz", 2.49, 2.79, 2022, "Consumer Reports"),
    ("Kettle Brand", "Sea Salt Chips", "chips", 8.0, 7.5, "oz", 4.29, 4.59, 2023, "r/shrinkflation"),
    ("Kettle Brand", "Backyard BBQ", "chips", 8.0, 7.5, "oz", 4.29, 4.59, 2023, "r/shrinkflation"),
    ("Cape Cod", "Original Kettle Cooked", "chips", 8.0, 7.5, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Stacy's", "Pita Chips Simply Naked", "chips", 7.33, 6.75, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Wise", "Original Potato Chips", "chips", 9.0, 7.75, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Takis", "Fuego", "chips", 9.9, 9.0, "oz", 4.99, 5.49, 2023, "r/shrinkflation"),
    ("Sensible Portions", "Garden Veggie Straws", "chips", 7.0, 6.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Skinny Pop", "Original Popcorn", "chips", 5.3, 4.4, "oz", 4.29, 4.49, 2023, "r/shrinkflation"),
    ("Frito-Lay", "Baked Lay's Original", "chips", 6.25, 5.5, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Frito-Lay", "Funyuns Original", "chips", 6.0, 5.5, "oz", 4.49, 4.79, 2022, "r/shrinkflation"),
    ("Snyder's", "Pretzel Pieces Honey Mustard & Onion", "chips", 12.0, 10.5, "oz", 4.29, 4.79, 2023, "r/shrinkflation"),
    ("Snyder's", "Mini Pretzels", "chips", 16.0, 15.0, "oz", 4.49, 4.99, 2023, "r/shrinkflation"),
    ("Utz", "Original Potato Chips", "chips", 9.5, 8.0, "oz", 3.99, 4.49, 2023, "r/shrinkflation"),
    ("Pirate's Booty", "Aged White Cheddar", "chips", 6.0, 5.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),

    # ================================================================
    # CEREAL
    # ================================================================
    ("General Mills", "Cheerios", "cereal", 18.0, 17.1, "oz", 5.99, 6.29, 2022, "Consumer Reports"),
    ("General Mills", "Honey Nut Cheerios", "cereal", 19.5, 18.8, "oz", 5.99, 6.49, 2022, "Consumer Reports"),
    ("General Mills", "Cinnamon Toast Crunch", "cereal", 19.3, 18.8, "oz", 5.99, 6.49, 2022, "BLS"),
    ("General Mills", "Lucky Charms", "cereal", 14.9, 14.0, "oz", 5.49, 5.99, 2022, "mouseprint.org"),
    ("General Mills", "Cocoa Puffs", "cereal", 15.2, 14.4, "oz", 5.49, 5.79, 2022, "mouseprint.org"),
    ("General Mills", "Trix", "cereal", 13.9, 13.0, "oz", 5.49, 5.79, 2022, "r/shrinkflation"),
    ("General Mills", "Golden Grahams", "cereal", 16.0, 14.9, "oz", 5.29, 5.79, 2022, "r/shrinkflation"),
    ("General Mills", "Reese's Puffs", "cereal", 16.0, 15.0, "oz", 5.49, 5.99, 2022, "r/shrinkflation"),
    ("Kellogg's", "Frosted Flakes", "cereal", 19.2, 17.7, "oz", 5.99, 6.29, 2022, "Consumer Reports"),
    ("Kellogg's", "Froot Loops", "cereal", 14.7, 13.2, "oz", 5.49, 5.79, 2022, "BLS"),
    ("Kellogg's", "Raisin Bran", "cereal", 18.7, 16.6, "oz", 5.49, 5.79, 2022, "Consumer Reports"),
    ("Kellogg's", "Special K Original", "cereal", 13.0, 12.0, "oz", 5.29, 5.49, 2023, "r/shrinkflation"),
    ("Kellogg's", "Rice Krispies", "cereal", 12.0, 10.3, "oz", 5.29, 5.49, 2023, "r/shrinkflation"),
    ("Kellogg's", "Apple Jacks", "cereal", 14.7, 13.2, "oz", 5.49, 5.79, 2022, "r/shrinkflation"),
    ("Kellogg's", "Corn Pops", "cereal", 13.1, 12.0, "oz", 5.49, 5.79, 2022, "r/shrinkflation"),
    ("Kellogg's", "Mini-Wheats", "cereal", 18.0, 16.5, "oz", 5.99, 6.29, 2022, "Consumer Reports"),
    ("Post", "Grape-Nuts", "cereal", 29.0, 24.0, "oz", 5.99, 5.99, 2021, "mouseprint.org"),
    ("Post", "Honeycomb", "cereal", 16.0, 14.5, "oz", 4.99, 5.29, 2022, "r/shrinkflation"),
    ("Post", "Fruity Pebbles", "cereal", 15.0, 13.0, "oz", 4.99, 5.29, 2022, "r/shrinkflation"),
    ("Post", "Cocoa Pebbles", "cereal", 15.0, 13.0, "oz", 4.99, 5.29, 2022, "r/shrinkflation"),
    ("Quaker", "Life Original", "cereal", 18.0, 16.9, "oz", 5.49, 5.79, 2022, "BLS"),
    ("Quaker", "Cap'n Crunch", "cereal", 14.0, 12.6, "oz", 5.29, 5.49, 2023, "r/shrinkflation"),
    ("Quaker", "Cap'n Crunch Berries", "cereal", 13.0, 11.5, "oz", 5.29, 5.49, 2023, "r/shrinkflation"),
    ("Malt-O-Meal", "Frosted Flakes (bag)", "cereal", 30.0, 28.0, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Malt-O-Meal", "Cocoa Dyno-Bites (bag)", "cereal", 28.0, 26.0, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),

    # ================================================================
    # BEVERAGES
    # ================================================================
    ("Tropicana", "Pure Premium Orange Juice", "beverages", 64.0, 52.0, "fl oz", 4.99, 4.99, 2022, "CNN/NYT"),
    ("Tropicana", "Lemonade", "beverages", 64.0, 52.0, "fl oz", 3.99, 3.99, 2022, "Consumer Reports"),
    ("Tropicana", "Ruby Red Grapefruit", "beverages", 64.0, 52.0, "fl oz", 4.99, 4.99, 2022, "Consumer Reports"),
    ("Minute Maid", "Orange Juice", "beverages", 64.0, 59.0, "fl oz", 4.49, 4.79, 2022, "BLS"),
    ("Minute Maid", "Lemonade", "beverages", 64.0, 59.0, "fl oz", 3.49, 3.79, 2022, "BLS"),
    ("Gatorade", "Thirst Quencher Lemon-Lime", "beverages", 32.0, 28.0, "fl oz", 2.49, 2.49, 2022, "WSJ/NPR"),
    ("Gatorade", "Fruit Punch", "beverages", 32.0, 28.0, "fl oz", 2.49, 2.49, 2022, "WSJ/NPR"),
    ("Gatorade", "Cool Blue", "beverages", 32.0, 28.0, "fl oz", 2.49, 2.49, 2022, "WSJ/NPR"),
    ("Gatorade", "Orange", "beverages", 32.0, 28.0, "fl oz", 2.49, 2.49, 2022, "WSJ/NPR"),
    ("Gatorade", "Glacier Freeze", "beverages", 32.0, 28.0, "fl oz", 2.49, 2.49, 2022, "WSJ/NPR"),
    ("Powerade", "Mountain Berry Blast", "beverages", 32.0, 28.0, "fl oz", 1.99, 1.99, 2022, "Consumer Reports"),
    ("Powerade", "Fruit Punch", "beverages", 32.0, 28.0, "fl oz", 1.99, 1.99, 2022, "Consumer Reports"),
    ("Powerade", "Lemon Lime", "beverages", 32.0, 28.0, "fl oz", 1.99, 1.99, 2022, "Consumer Reports"),
    ("Simply", "Orange Juice", "beverages", 52.0, 46.0, "fl oz", 4.99, 5.29, 2023, "r/shrinkflation"),
    ("Simply", "Lemonade", "beverages", 52.0, 46.0, "fl oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Ocean Spray", "Cranberry Juice Cocktail", "beverages", 64.0, 60.0, "fl oz", 4.49, 4.79, 2023, "mouseprint.org"),
    ("Snapple", "Peach Tea", "beverages", 64.0, 52.0, "fl oz", 4.49, 4.49, 2022, "r/shrinkflation"),
    # Removed: Arizona Green Tea — Arizona is known for NOT shrinking products
    ("V8", "Splash Berry Blend", "beverages", 64.0, 46.0, "fl oz", 3.99, 3.99, 2022, "mouseprint.org"),
    # Removed: Hawaiian Punch 128→96oz — unverified 25% reduction, too extreme
    ("Country Time", "Lemonade Mix", "beverages", 19.0, 16.0, "oz", 4.49, 4.79, 2022, "r/shrinkflation"),
    ("Crystal Light", "Lemonade Mix", "beverages", 3.2, 2.5, "oz", 3.49, 3.69, 2023, "r/shrinkflation"),

    # ================================================================
    # COFFEE
    # ================================================================
    ("Folgers", "Classic Roast Ground Coffee", "coffee", 51.0, 43.5, "oz", 12.99, 13.49, 2022, "BLS/mouseprint.org"),
    ("Folgers", "Black Silk", "coffee", 24.2, 22.6, "oz", 9.99, 10.49, 2022, "mouseprint.org"),
    ("Folgers", "Breakfast Blend", "coffee", 25.4, 22.6, "oz", 9.99, 10.49, 2023, "r/shrinkflation"),
    ("Folgers", "Colombian", "coffee", 24.2, 22.6, "oz", 10.49, 10.99, 2022, "mouseprint.org"),
    ("Folgers", "1850 Pioneer Blend", "coffee", 12.0, 10.0, "oz", 8.99, 9.49, 2023, "r/shrinkflation"),
    ("Maxwell House", "Original Roast", "coffee", 30.6, 24.5, "oz", 9.99, 10.49, 2022, "Consumer Reports"),
    ("Maxwell House", "French Roast", "coffee", 25.6, 24.5, "oz", 9.99, 10.49, 2022, "Consumer Reports"),
    ("Maxwell House", "House Blend", "coffee", 24.5, 22.0, "oz", 9.49, 9.99, 2023, "r/shrinkflation"),
    ("Starbucks", "Pike Place Roast Ground", "coffee", 20.0, 18.0, "oz", 12.99, 13.49, 2023, "r/shrinkflation"),
    ("Starbucks", "French Roast Ground", "coffee", 20.0, 18.0, "oz", 12.99, 13.49, 2023, "r/shrinkflation"),
    ("Starbucks", "House Blend Ground", "coffee", 20.0, 18.0, "oz", 12.99, 13.49, 2023, "r/shrinkflation"),
    ("Starbucks", "Breakfast Blend Ground", "coffee", 20.0, 18.0, "oz", 12.99, 13.49, 2023, "r/shrinkflation"),
    ("Dunkin'", "Original Blend Ground", "coffee", 22.0, 20.0, "oz", 10.99, 11.49, 2023, "r/shrinkflation"),
    ("Dunkin'", "French Vanilla Ground", "coffee", 22.0, 20.0, "oz", 10.99, 11.49, 2023, "r/shrinkflation"),
    ("Peet's", "Major Dickason's Blend", "coffee", 12.0, 10.5, "oz", 10.99, 11.49, 2023, "Consumer Reports"),
    ("Peet's", "French Roast", "coffee", 12.0, 10.5, "oz", 10.99, 11.49, 2023, "Consumer Reports"),
    ("Eight O'Clock", "Original Ground", "coffee", 24.0, 21.0, "oz", 8.99, 9.49, 2022, "r/shrinkflation"),
    ("Nescafe", "Clasico Instant", "coffee", 10.5, 9.0, "oz", 9.99, 10.49, 2023, "r/shrinkflation"),
    ("Cafe Bustelo", "Espresso Ground", "coffee", 10.0, 9.0, "oz", 5.99, 6.49, 2023, "r/shrinkflation"),
    ("Tim Hortons", "Original Blend Ground", "coffee", 24.0, 22.0, "oz", 10.99, 11.49, 2023, "r/shrinkflation"),
    ("McCafe", "Premium Roast Ground", "coffee", 12.0, 10.0, "oz", 7.99, 8.49, 2023, "r/shrinkflation"),
    ("Chock Full o'Nuts", "Original Heavenly", "coffee", 26.0, 23.0, "oz", 8.99, 9.49, 2022, "r/shrinkflation"),

    # ================================================================
    # COOKIES
    # ================================================================
    ("Nabisco", "Oreo Original", "cookies", 15.35, 13.29, "oz", 4.99, 5.49, 2022, "Consumer Reports"),
    ("Nabisco", "Oreo Double Stuf", "cookies", 15.35, 14.03, "oz", 5.49, 5.99, 2022, "Consumer Reports"),
    ("Nabisco", "Oreo Golden", "cookies", 15.35, 13.29, "oz", 4.99, 5.49, 2022, "Consumer Reports"),
    ("Nabisco", "Oreo Mint", "cookies", 15.25, 13.2, "oz", 5.49, 5.99, 2023, "r/shrinkflation"),
    ("Nabisco", "Chips Ahoy! Original", "cookies", 13.0, 11.75, "oz", 4.49, 4.99, 2022, "mouseprint.org"),
    ("Nabisco", "Chips Ahoy! Chewy", "cookies", 13.0, 11.75, "oz", 4.49, 4.99, 2022, "mouseprint.org"),
    ("Nabisco", "Chips Ahoy! Chunky", "cookies", 11.75, 10.25, "oz", 4.49, 4.99, 2023, "r/shrinkflation"),
    ("Nabisco", "Nutter Butter", "cookies", 12.0, 10.5, "oz", 4.29, 4.69, 2023, "r/shrinkflation"),
    ("Nabisco", "Fig Newtons", "cookies", 10.0, 9.0, "oz", 4.49, 4.99, 2022, "mouseprint.org"),
    ("Pepperidge Farm", "Milano Cookies", "cookies", 7.5, 6.75, "oz", 4.99, 5.29, 2022, "Consumer Reports"),
    ("Pepperidge Farm", "Chessmen Cookies", "cookies", 7.25, 6.6, "oz", 4.49, 4.79, 2022, "mouseprint.org"),
    ("Pepperidge Farm", "Sausalito Cookies", "cookies", 7.2, 6.8, "oz", 4.99, 5.29, 2023, "r/shrinkflation"),
    ("Pepperidge Farm", "Geneva Cookies", "cookies", 5.5, 4.9, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Pepperidge Farm", "Goldfish Mega Bites Cheddar", "cookies", 5.9, 5.0, "oz", 3.49, 3.79, 2023, "r/shrinkflation"),
    ("Keebler", "Fudge Stripes", "cookies", 11.5, 10.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Keebler", "E.L. Fudge", "cookies", 12.0, 10.6, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Girl Scout Cookies", "Thin Mints", "cookies", 9.0, 8.0, "oz", 6.00, 6.00, 2024, "NPR/r/shrinkflation"),
    ("Girl Scout Cookies", "Samoas", "cookies", 7.5, 6.5, "oz", 6.00, 6.00, 2024, "NPR/r/shrinkflation"),
    ("Famous Amos", "Chocolate Chip", "cookies", 12.4, 11.0, "oz", 4.99, 5.29, 2023, "r/shrinkflation"),
    ("Voortman", "Wafers Chocolate", "cookies", 10.6, 9.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),

    # ================================================================
    # CRACKERS
    # ================================================================
    ("Nabisco", "Wheat Thins Original", "crackers", 10.0, 8.5, "oz", 4.49, 4.99, 2022, "mouseprint.org"),
    ("Nabisco", "Triscuit Original", "crackers", 9.5, 8.5, "oz", 4.79, 5.29, 2022, "Consumer Reports"),
    ("Nabisco", "Triscuit Fire Roasted Tomato", "crackers", 9.0, 8.0, "oz", 4.79, 5.29, 2022, "Consumer Reports"),
    ("Nabisco", "Ritz Crackers", "crackers", 13.7, 12.2, "oz", 4.99, 5.49, 2022, "mouseprint.org"),
    ("Nabisco", "Ritz Bits Cheese", "crackers", 8.8, 7.7, "oz", 4.49, 4.99, 2023, "r/shrinkflation"),
    ("Keebler", "Club Crackers", "crackers", 13.7, 12.5, "oz", 4.29, 4.69, 2023, "r/shrinkflation"),
    ("Keebler", "Town House Crackers", "crackers", 13.8, 12.4, "oz", 4.29, 4.69, 2023, "r/shrinkflation"),
    ("Cheez-It", "Original", "crackers", 12.4, 11.5, "oz", 4.49, 4.99, 2022, "mouseprint.org"),
    ("Cheez-It", "White Cheddar", "crackers", 12.4, 11.5, "oz", 4.49, 4.99, 2022, "mouseprint.org"),
    ("Cheez-It", "Grooves", "crackers", 9.0, 8.0, "oz", 4.49, 4.99, 2023, "r/shrinkflation"),
    ("Goldfish", "Cheddar Crackers", "crackers", 6.6, 6.0, "oz", 2.79, 3.09, 2023, "r/shrinkflation"),
    ("Goldfish", "Pizza Crackers", "crackers", 6.6, 6.0, "oz", 2.79, 3.09, 2023, "r/shrinkflation"),
    ("Premium", "Saltine Crackers", "crackers", 16.0, 14.4, "oz", 4.49, 4.99, 2023, "r/shrinkflation"),
    ("Chicken in a Biskit", "Original", "crackers", 7.5, 6.5, "oz", 4.29, 4.79, 2023, "r/shrinkflation"),
    ("Carr's", "Table Water Crackers", "crackers", 4.25, 3.5, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Lance", "Captain's Wafers Cream Cheese", "crackers", 5.5, 4.8, "oz", 3.49, 3.79, 2023, "r/shrinkflation"),

    # ================================================================
    # YOGURT
    # ================================================================
    ("Chobani", "Greek Yogurt Vanilla", "yogurt", 6.0, 5.3, "oz", 1.49, 1.49, 2021, "Consumer Reports"),
    ("Chobani", "Greek Yogurt Strawberry", "yogurt", 6.0, 5.3, "oz", 1.49, 1.49, 2021, "Consumer Reports"),
    ("Chobani", "Greek Yogurt Blueberry", "yogurt", 6.0, 5.3, "oz", 1.49, 1.49, 2021, "Consumer Reports"),
    ("Chobani", "Greek Yogurt Peach", "yogurt", 6.0, 5.3, "oz", 1.49, 1.49, 2021, "Consumer Reports"),
    ("Chobani", "Greek Yogurt Mango", "yogurt", 6.0, 5.3, "oz", 1.49, 1.49, 2021, "Consumer Reports"),
    ("Chobani", "Flip Almond Coco Loco", "yogurt", 5.3, 4.5, "oz", 1.79, 1.79, 2023, "r/shrinkflation"),
    ("Dannon", "Oikos Triple Zero Vanilla", "yogurt", 5.3, 4.9, "oz", 1.29, 1.49, 2023, "r/shrinkflation"),
    ("Dannon", "Oikos Triple Zero Mixed Berry", "yogurt", 5.3, 4.9, "oz", 1.29, 1.49, 2023, "r/shrinkflation"),
    ("Dannon", "Light & Fit Vanilla", "yogurt", 6.0, 5.3, "oz", 0.99, 1.19, 2022, "mouseprint.org"),
    ("Dannon", "Light & Fit Strawberry", "yogurt", 6.0, 5.3, "oz", 0.99, 1.19, 2022, "mouseprint.org"),
    ("Yoplait", "Original Strawberry", "yogurt", 6.0, 5.3, "oz", 0.89, 0.99, 2021, "BLS"),
    ("Yoplait", "Original French Vanilla", "yogurt", 6.0, 5.3, "oz", 0.89, 0.99, 2021, "BLS"),
    ("Yoplait", "Original Harvest Peach", "yogurt", 6.0, 5.3, "oz", 0.89, 0.99, 2021, "BLS"),
    ("Yoplait", "Go-Gurt (8-pack)", "yogurt", 2.25, 2.0, "oz each", 3.49, 3.49, 2022, "mouseprint.org"),
    ("Fage", "Total 0% Plain", "yogurt", 7.0, 5.3, "oz", 1.99, 1.99, 2022, "Consumer Reports"),
    ("Fage", "Total 2% Mixed Berry", "yogurt", 7.0, 5.3, "oz", 1.99, 1.99, 2022, "Consumer Reports"),
    ("Noosa", "Strawberry Yoghurt", "yogurt", 8.0, 7.0, "oz", 2.49, 2.49, 2023, "r/shrinkflation"),
    ("Noosa", "Blueberry Yoghurt", "yogurt", 8.0, 7.0, "oz", 2.49, 2.49, 2023, "r/shrinkflation"),
    ("Siggi's", "Vanilla Skyr", "yogurt", 5.3, 4.4, "oz", 1.99, 1.99, 2023, "r/shrinkflation"),
    ("Siggi's", "Strawberry Skyr", "yogurt", 5.3, 4.4, "oz", 1.99, 1.99, 2023, "r/shrinkflation"),
    ("Stonyfield", "Organic Vanilla", "yogurt", 6.0, 5.3, "oz", 1.49, 1.49, 2023, "r/shrinkflation"),
    ("Two Good", "Vanilla Greek Yogurt", "yogurt", 5.3, 5.0, "oz", 1.49, 1.69, 2023, "r/shrinkflation"),

    # ================================================================
    # CONDIMENTS
    # ================================================================
    ("Heinz", "Tomato Ketchup", "condiments", 38.0, 32.0, "oz", 4.99, 5.29, 2022, "Consumer Reports"),
    ("Heinz", "Yellow Mustard", "condiments", 20.0, 17.5, "oz", 2.99, 3.29, 2022, "mouseprint.org"),
    ("Heinz", "Sweet Relish", "condiments", 16.0, 13.0, "oz", 3.49, 3.79, 2023, "r/shrinkflation"),
    ("French's", "Classic Yellow Mustard", "condiments", 14.0, 12.0, "oz", 2.49, 2.79, 2023, "r/shrinkflation"),
    ("Hellmann's", "Real Mayonnaise", "condiments", 30.0, 25.0, "oz", 5.99, 6.49, 2022, "Consumer Reports"),
    ("Hellmann's", "Light Mayonnaise", "condiments", 30.0, 25.0, "oz", 5.79, 6.29, 2022, "Consumer Reports"),
    ("Hellmann's", "Vegan Mayo", "condiments", 24.0, 20.0, "oz", 5.99, 6.49, 2023, "r/shrinkflation"),
    ("Kraft", "Mayo", "condiments", 30.0, 22.0, "oz", 5.49, 5.99, 2023, "mouseprint.org"),
    ("Kraft", "Miracle Whip", "condiments", 30.0, 22.0, "oz", 5.29, 5.79, 2023, "mouseprint.org"),
    ("Skippy", "Creamy Peanut Butter", "condiments", 18.0, 16.3, "oz", 4.49, 4.99, 2022, "CNN/mouseprint.org"),
    ("Skippy", "Chunky Peanut Butter", "condiments", 18.0, 16.3, "oz", 4.49, 4.99, 2022, "CNN/mouseprint.org"),
    ("Skippy", "Natural Creamy", "condiments", 15.0, 13.5, "oz", 4.79, 5.29, 2023, "r/shrinkflation"),
    ("Jif", "Creamy Peanut Butter", "condiments", 18.0, 15.5, "oz", 4.29, 4.79, 2023, "r/shrinkflation"),
    ("Jif", "Crunchy Peanut Butter", "condiments", 18.0, 15.5, "oz", 4.29, 4.79, 2023, "r/shrinkflation"),
    ("Hidden Valley", "Original Ranch Dressing", "condiments", 24.0, 20.0, "oz", 4.99, 5.29, 2023, "r/shrinkflation"),
    ("Hidden Valley", "Ranch Dip Mix", "condiments", 1.0, 0.8, "oz", 1.49, 1.69, 2023, "r/shrinkflation"),
    ("Best Foods", "Real Mayonnaise", "condiments", 30.0, 25.0, "oz", 5.99, 6.49, 2022, "Consumer Reports"),
    ("Peter Pan", "Creamy Peanut Butter", "condiments", 16.3, 14.0, "oz", 3.99, 4.49, 2023, "r/shrinkflation"),
    ("Smucker's", "Strawberry Jam", "condiments", 18.0, 15.5, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Welch's", "Grape Jelly", "condiments", 30.0, 27.0, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),

    # ================================================================
    # CHEESE
    # ================================================================
    ("Kraft", "American Singles", "cheese", 24.0, 22.0, "oz", 5.99, 6.49, 2022, "Consumer Reports"),
    ("Kraft", "Shredded Cheddar", "cheese", 8.0, 7.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Kraft", "Shredded Mozzarella", "cheese", 8.0, 7.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Kraft", "String Cheese 12-pack", "cheese", 12.0, 10.0, "oz", 5.49, 5.99, 2023, "r/shrinkflation"),
    ("Sargento", "Sliced Provolone", "cheese", 8.0, 7.0, "oz", 4.49, 4.99, 2022, "mouseprint.org"),
    ("Sargento", "Sliced Swiss", "cheese", 8.0, 7.0, "oz", 4.49, 4.99, 2022, "mouseprint.org"),
    ("Sargento", "Balanced Breaks Snack", "cheese", 4.5, 3.9, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Sargento", "Shredded Sharp Cheddar", "cheese", 8.0, 7.0, "oz", 4.49, 4.99, 2023, "r/shrinkflation"),
    ("Tillamook", "Medium Cheddar Block", "cheese", 32.0, 28.0, "oz", 8.99, 9.49, 2023, "r/shrinkflation"),
    ("Tillamook", "Extra Sharp Cheddar Block", "cheese", 32.0, 28.0, "oz", 8.99, 9.49, 2023, "r/shrinkflation"),
    ("Cracker Barrel", "Sharp Cheddar", "cheese", 10.0, 8.0, "oz", 4.99, 5.29, 2022, "Consumer Reports"),
    ("Cracker Barrel", "Extra Sharp Cheddar", "cheese", 10.0, 8.0, "oz", 4.99, 5.29, 2022, "Consumer Reports"),
    ("Laughing Cow", "Original Creamy Swiss", "cheese", 6.0, 5.4, "oz", 4.29, 4.49, 2023, "mouseprint.org"),
    ("Babybel", "Original Mini", "cheese", 7.5, 6.3, "oz", 5.99, 6.29, 2023, "r/shrinkflation"),
    ("Philadelphia", "Original Cream Cheese", "cheese", 8.0, 7.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Borden", "American Singles", "cheese", 16.0, 14.0, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Velveeta", "Original Block", "cheese", 32.0, 28.0, "oz", 7.99, 8.49, 2023, "r/shrinkflation"),

    # ================================================================
    # BREAD & BAKED GOODS
    # ================================================================
    ("Nature's Own", "Honey Wheat Bread", "bread", 20.0, 18.0, "oz", 4.29, 4.49, 2023, "r/shrinkflation"),
    ("Nature's Own", "100% Whole Wheat", "bread", 20.0, 18.0, "oz", 4.29, 4.49, 2023, "r/shrinkflation"),
    ("Sara Lee", "Artesano White Bread", "bread", 20.0, 18.0, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Sara Lee", "Honey Wheat Bread", "bread", 20.0, 18.0, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Dave's Killer Bread", "21 Whole Grains", "bread", 27.0, 24.0, "oz", 6.29, 6.49, 2023, "r/shrinkflation"),
    ("Dave's Killer Bread", "Good Seed", "bread", 27.0, 24.0, "oz", 6.29, 6.49, 2023, "r/shrinkflation"),
    ("King's Hawaiian", "Sweet Rolls (12-pack)", "bread", 24.0, 20.0, "oz", 5.49, 5.99, 2022, "mouseprint.org"),
    ("Thomas'", "English Muffins (6-pack)", "bread", 13.0, 12.0, "oz", 4.79, 4.99, 2023, "r/shrinkflation"),
    ("Thomas'", "Bagels Everything (6-pack)", "bread", 20.0, 18.0, "oz", 5.29, 5.49, 2023, "r/shrinkflation"),
    ("Arnold", "Whole Wheat Bread", "bread", 24.0, 22.0, "oz", 5.49, 5.69, 2023, "r/shrinkflation"),
    ("Pepperidge Farm", "Farmhouse White", "bread", 24.0, 22.0, "oz", 4.99, 5.29, 2023, "r/shrinkflation"),
    ("Pepperidge Farm", "Swirl Cinnamon", "bread", 16.0, 14.0, "oz", 4.99, 5.29, 2023, "r/shrinkflation"),
    ("Ball Park", "Hot Dog Buns (8-pack)", "bread", 12.0, 11.0, "oz", 3.49, 3.79, 2022, "r/shrinkflation"),
    ("Martin's", "Potato Rolls (12-pack)", "bread", 18.0, 15.0, "oz", 4.99, 5.29, 2023, "r/shrinkflation"),
    ("Bimbo", "Soft White Bread", "bread", 20.0, 18.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Entenmann's", "Rich Frosted Donuts", "bread", 17.0, 15.0, "oz", 5.49, 5.99, 2022, "mouseprint.org"),
    ("Little Debbie", "Swiss Rolls (12-pack)", "bread", 13.0, 11.0, "oz", 3.49, 3.79, 2023, "r/shrinkflation"),
    ("Hostess", "Twinkies (10-pack)", "bread", 13.5, 11.5, "oz", 4.99, 5.29, 2023, "r/shrinkflation"),

    # ================================================================
    # PASTA & GRAINS
    # ================================================================
    ("Barilla", "Spaghetti", "pasta", 16.0, 14.5, "oz", 1.89, 2.19, 2023, "r/shrinkflation"),
    ("Barilla", "Penne", "pasta", 16.0, 14.5, "oz", 1.89, 2.19, 2023, "r/shrinkflation"),
    ("Barilla", "Rotini", "pasta", 16.0, 14.5, "oz", 1.89, 2.19, 2023, "r/shrinkflation"),
    ("De Cecco", "Rigatoni", "pasta", 16.0, 13.25, "oz", 3.29, 3.49, 2023, "r/shrinkflation"),
    ("De Cecco", "Spaghetti", "pasta", 16.0, 13.25, "oz", 3.29, 3.49, 2023, "r/shrinkflation"),
    ("Ronzoni", "Rotini", "pasta", 16.0, 12.0, "oz", 1.79, 1.99, 2023, "mouseprint.org"),
    ("Ronzoni", "Penne", "pasta", 16.0, 12.0, "oz", 1.79, 1.99, 2023, "mouseprint.org"),
    ("Ronzoni", "Spaghetti", "pasta", 16.0, 12.0, "oz", 1.79, 1.99, 2023, "mouseprint.org"),
    ("Mueller's", "Spaghetti", "pasta", 16.0, 12.0, "oz", 1.49, 1.79, 2023, "mouseprint.org"),
    ("Mueller's", "Elbow Macaroni", "pasta", 16.0, 12.0, "oz", 1.49, 1.79, 2023, "mouseprint.org"),
    ("Uncle Ben's/Ben's Original", "Converted Rice", "pasta", 32.0, 28.0, "oz", 4.99, 5.29, 2022, "Consumer Reports"),
    ("Uncle Ben's/Ben's Original", "Ready Rice Jasmine", "pasta", 8.8, 8.5, "oz", 2.49, 2.79, 2023, "r/shrinkflation"),
    ("Kraft", "Mac & Cheese Original", "pasta", 7.25, 6.0, "oz", 1.49, 1.79, 2023, "r/shrinkflation"),
    ("Velveeta", "Shells & Cheese", "pasta", 12.0, 10.1, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Annie's", "Mac & Cheese Classic", "pasta", 6.0, 5.25, "oz", 2.49, 2.79, 2023, "r/shrinkflation"),
    ("Rice-A-Roni", "Chicken Flavor", "pasta", 6.9, 5.9, "oz", 1.49, 1.79, 2023, "r/shrinkflation"),
    ("Knorr", "Pasta Sides Alfredo", "pasta", 4.4, 3.8, "oz", 1.49, 1.79, 2023, "r/shrinkflation"),

    # ================================================================
    # CANDY & CHOCOLATE
    # ================================================================
    ("Mars", "Snickers Bar", "candy", 2.07, 1.86, "oz", 1.79, 1.99, 2022, "BLS"),
    ("Mars", "M&M's Peanut", "candy", 10.7, 10.0, "oz", 4.99, 5.49, 2023, "r/shrinkflation"),
    ("Mars", "M&M's Plain", "candy", 10.7, 10.0, "oz", 4.99, 5.49, 2023, "r/shrinkflation"),
    ("Mars", "Twix Bar", "candy", 1.79, 1.68, "oz", 1.79, 1.99, 2022, "BLS"),
    ("Mars", "Milky Way Bar", "candy", 1.84, 1.74, "oz", 1.79, 1.99, 2022, "BLS"),
    ("Mars", "3 Musketeers Bar", "candy", 2.13, 1.92, "oz", 1.79, 1.99, 2022, "BLS"),
    ("Mars", "Skittles Original", "candy", 4.0, 3.3, "oz", 2.29, 2.49, 2023, "r/shrinkflation"),
    ("Hershey's", "Milk Chocolate Bar", "candy", 1.55, 1.44, "oz", 1.79, 1.99, 2022, "Consumer Reports"),
    ("Hershey's", "Reese's Peanut Butter Cups", "candy", 1.6, 1.4, "oz", 1.79, 1.99, 2022, "Consumer Reports"),
    ("Hershey's", "Kit Kat", "candy", 1.5, 1.4, "oz", 1.79, 1.99, 2023, "r/shrinkflation"),
    ("Hershey's", "Almond Joy", "candy", 1.61, 1.41, "oz", 1.79, 1.99, 2023, "r/shrinkflation"),
    ("Hershey's", "Kisses Milk Chocolate", "candy", 10.0, 9.0, "oz", 5.49, 5.99, 2023, "r/shrinkflation"),
    ("Hershey's", "Reese's Pieces", "candy", 9.9, 9.0, "oz", 5.49, 5.99, 2023, "r/shrinkflation"),
    ("Mondelez", "Cadbury Dairy Milk", "candy", 3.5, 3.17, "oz", 2.49, 2.79, 2022, "BBC/Consumer Reports"),
    ("Mondelez", "Toblerone", "candy", 3.52, 3.17, "oz", 4.99, 4.99, 2022, "BBC/WSJ"),
    ("Mondelez", "Swedish Fish", "candy", 5.0, 3.6, "oz", 2.49, 2.79, 2023, "r/shrinkflation"),
    ("Mondelez", "Sour Patch Kids", "candy", 5.0, 3.5, "oz", 2.49, 2.79, 2023, "r/shrinkflation"),
    ("Ferrara", "Nerds Gummy Clusters", "candy", 8.0, 7.0, "oz", 4.49, 4.99, 2023, "r/shrinkflation"),
    ("Ferrara", "Trolli Sour Brite Crawlers", "candy", 7.2, 6.3, "oz", 3.49, 3.79, 2023, "r/shrinkflation"),
    ("Haribo", "Goldbears", "candy", 5.0, 4.0, "oz", 2.49, 2.79, 2023, "r/shrinkflation"),
    ("Haribo", "Twin Snakes", "candy", 5.0, 4.0, "oz", 2.49, 2.79, 2023, "r/shrinkflation"),
    ("Nestle", "Butterfinger", "candy", 1.9, 1.7, "oz", 1.79, 1.99, 2022, "BLS"),
    ("Nestle", "Baby Ruth", "candy", 2.1, 1.9, "oz", 1.79, 1.99, 2022, "BLS"),
    ("Wrigley's", "Extra Gum (15-stick pack)", "candy", 15.0, 12.0, "sticks", 1.49, 1.79, 2023, "r/shrinkflation"),
    ("Tootsie Roll", "Tootsie Pops (bag)", "candy", 10.13, 9.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),

    # ================================================================
    # HOUSEHOLD — toilet paper, paper towels, cleaning, etc.
    # ================================================================
    ("Charmin", "Ultra Soft (Mega Roll)", "household", 352.0, 312.0, "sheets", 13.99, 14.99, 2022, "Consumer Reports"),
    ("Charmin", "Ultra Strong (Mega Roll)", "household", 352.0, 312.0, "sheets", 13.99, 14.99, 2022, "Consumer Reports"),
    ("Charmin", "Essentials Strong", "household", 352.0, 300.0, "sheets", 11.99, 12.49, 2023, "r/shrinkflation"),
    ("Bounty", "Select-A-Size (Double Roll)", "household", 110.0, 98.0, "sheets", 12.99, 13.49, 2022, "mouseprint.org"),
    ("Bounty", "Essentials (Full Sheet)", "household", 74.0, 64.0, "sheets", 9.99, 10.49, 2023, "r/shrinkflation"),
    ("Cottonelle", "CleanCare (Mega Roll)", "household", 340.0, 312.0, "sheets", 12.99, 13.49, 2022, "Consumer Reports"),
    ("Cottonelle", "Ultra ComfortCare", "household", 284.0, 268.0, "sheets", 12.99, 13.49, 2023, "r/shrinkflation"),
    ("Scott", "1000 Sheets (1-ply)", "household", 1000.0, 900.0, "sheets", 1.49, 1.49, 2023, "r/shrinkflation"),
    ("Angel Soft", "Bath Tissue (Mega Roll)", "household", 320.0, 280.0, "sheets", 8.99, 9.49, 2023, "r/shrinkflation"),
    ("Dawn", "Ultra Dishwashing Liquid", "household", 19.4, 18.0, "fl oz", 3.99, 4.29, 2022, "mouseprint.org"),
    ("Dawn", "Platinum Dishwashing Liquid", "household", 24.0, 22.0, "fl oz", 4.99, 5.29, 2023, "r/shrinkflation"),
    ("Tide", "Original Liquid Detergent", "household", 92.0, 84.0, "fl oz", 13.99, 14.49, 2022, "Consumer Reports"),
    ("Tide", "Free & Gentle", "household", 92.0, 84.0, "fl oz", 14.49, 14.99, 2022, "Consumer Reports"),
    ("Tide", "Pods (42-count)", "household", 42.0, 39.0, "count", 14.99, 15.49, 2023, "r/shrinkflation"),
    ("Gain", "Original Liquid Detergent", "household", 92.0, 84.0, "fl oz", 12.99, 13.49, 2022, "Consumer Reports"),
    ("Downy", "Ultra Fabric Softener", "household", 51.0, 44.0, "fl oz", 6.99, 7.49, 2023, "r/shrinkflation"),
    ("Cascade", "Platinum ActionPacs", "household", 62.0, 52.0, "count", 19.99, 20.49, 2023, "r/shrinkflation"),
    ("Crest", "3D White Toothpaste", "household", 6.4, 5.7, "oz", 4.99, 5.29, 2023, "r/shrinkflation"),
    ("Crest", "Pro-Health Toothpaste", "household", 6.0, 5.2, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Colgate", "Total Whitening", "household", 6.0, 5.1, "oz", 5.49, 5.79, 2023, "r/shrinkflation"),
    ("Dove", "Beauty Bar (8-pack)", "household", 4.0, 3.75, "oz each", 10.99, 11.49, 2023, "r/shrinkflation"),
    ("Irish Spring", "Original Bar Soap (8-pack)", "household", 3.75, 3.2, "oz each", 6.99, 7.49, 2023, "r/shrinkflation"),
    ("Glad", "ForceFlex Tall Kitchen Bags", "household", 80.0, 72.0, "count", 14.99, 15.49, 2023, "r/shrinkflation"),
    ("Hefty", "Ultra Strong Tall Kitchen Bags", "household", 80.0, 74.0, "count", 13.99, 14.49, 2023, "r/shrinkflation"),
    ("Kleenex", "Ultra Soft Facial Tissue", "household", 120.0, 110.0, "count", 2.49, 2.69, 2022, "mouseprint.org"),
    ("Puffs", "Plus Lotion Facial Tissue", "household", 124.0, 112.0, "count", 2.49, 2.69, 2023, "r/shrinkflation"),

    # ================================================================
    # FROZEN FOOD
    # ================================================================
    ("Stouffer's", "Lasagna Family Size", "frozen food", 38.0, 32.0, "oz", 8.99, 9.49, 2022, "Consumer Reports"),
    ("Stouffer's", "Mac & Cheese Family Size", "frozen food", 40.0, 36.0, "oz", 7.99, 8.49, 2022, "Consumer Reports"),
    ("Stouffer's", "Chicken Alfredo", "frozen food", 12.0, 10.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("DiGiorno", "Rising Crust Pepperoni Pizza", "frozen food", 29.6, 27.5, "oz", 7.49, 7.99, 2022, "mouseprint.org"),
    ("DiGiorno", "Rising Crust Supreme Pizza", "frozen food", 31.5, 29.2, "oz", 7.99, 8.49, 2022, "mouseprint.org"),
    ("DiGiorno", "Stuffed Crust Pepperoni", "frozen food", 22.2, 20.0, "oz", 7.99, 8.49, 2023, "r/shrinkflation"),
    ("Hot Pockets", "Pepperoni Pizza (2-pack)", "frozen food", 9.0, 8.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Hot Pockets", "Ham & Cheese (2-pack)", "frozen food", 9.0, 8.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Marie Callender's", "Chicken Pot Pie", "frozen food", 16.5, 15.0, "oz", 4.49, 4.99, 2022, "mouseprint.org"),
    ("Marie Callender's", "Beef Pot Pie", "frozen food", 16.5, 15.0, "oz", 4.49, 4.99, 2022, "mouseprint.org"),
    ("Eggo", "Homestyle Waffles (10-pack)", "frozen food", 12.3, 10.9, "oz", 3.99, 4.29, 2022, "BLS"),
    ("Eggo", "Blueberry Waffles (10-pack)", "frozen food", 12.3, 10.9, "oz", 3.99, 4.29, 2022, "BLS"),
    ("Lean Cuisine", "Chicken Alfredo", "frozen food", 10.0, 8.0, "oz", 3.49, 3.79, 2023, "r/shrinkflation"),
    ("Lean Cuisine", "Spaghetti with Meat Sauce", "frozen food", 11.5, 9.5, "oz", 3.49, 3.79, 2023, "r/shrinkflation"),
    ("Banquet", "Chicken Pot Pie", "frozen food", 7.0, 6.5, "oz", 1.29, 1.49, 2023, "r/shrinkflation"),
    ("Banquet", "Salisbury Steak Dinner", "frozen food", 11.88, 10.5, "oz", 1.99, 2.29, 2023, "r/shrinkflation"),
    ("Birds Eye", "Steamfresh Mixed Vegetables", "frozen food", 12.0, 10.8, "oz", 2.99, 3.29, 2023, "r/shrinkflation"),
    ("Birds Eye", "Steamfresh Broccoli Florets", "frozen food", 12.0, 10.8, "oz", 2.99, 3.29, 2023, "r/shrinkflation"),
    ("Green Giant", "Steamers Broccoli & Cheese", "frozen food", 10.0, 8.0, "oz", 2.99, 3.29, 2023, "r/shrinkflation"),
    ("Totino's", "Party Pizza Pepperoni", "frozen food", 10.2, 9.8, "oz", 2.29, 2.69, 2022, "r/shrinkflation"),
    ("Tombstone", "Original Pepperoni Pizza", "frozen food", 21.6, 19.3, "oz", 5.99, 6.29, 2023, "r/shrinkflation"),
    ("El Monterey", "Beef & Bean Burritos (8-pack)", "frozen food", 32.0, 28.0, "oz", 5.99, 6.29, 2023, "r/shrinkflation"),
    ("TGI Friday's", "Mozzarella Sticks", "frozen food", 17.4, 15.0, "oz", 7.99, 8.49, 2023, "r/shrinkflation"),
    ("Jimmy Dean", "Breakfast Sandwiches (4-pack)", "frozen food", 18.4, 16.0, "oz", 6.99, 7.49, 2023, "r/shrinkflation"),
    ("Ore-Ida", "Golden Fries", "frozen food", 32.0, 28.0, "oz", 4.99, 5.29, 2023, "r/shrinkflation"),

    # ================================================================
    # CANNED GOODS — soup, vegetables, fruits, tuna
    # ================================================================
    ("Campbell's", "Condensed Tomato Soup", "canned goods", 10.75, 10.5, "oz", 1.29, 1.49, 2022, "mouseprint.org"),
    ("Campbell's", "Condensed Chicken Noodle Soup", "canned goods", 10.75, 10.5, "oz", 1.49, 1.69, 2022, "mouseprint.org"),
    ("Campbell's", "Chunky Classic Chicken Noodle", "canned goods", 18.6, 16.1, "oz", 2.99, 3.29, 2023, "r/shrinkflation"),
    ("Campbell's", "Chunky Sirloin Burger", "canned goods", 18.8, 16.3, "oz", 2.99, 3.29, 2023, "r/shrinkflation"),
    ("Campbell's", "SpaghettiOs Original", "canned goods", 15.8, 15.0, "oz", 1.49, 1.79, 2023, "r/shrinkflation"),
    ("Progresso", "Traditional Chicken Noodle", "canned goods", 19.0, 18.5, "oz", 2.99, 3.29, 2022, "r/shrinkflation"),
    ("Progresso", "Rich & Hearty Beef Stew", "canned goods", 18.5, 17.0, "oz", 3.29, 3.49, 2023, "r/shrinkflation"),
    ("StarKist", "Chunk Light Tuna in Water", "canned goods", 5.0, 4.5, "oz", 1.29, 1.49, 2022, "Consumer Reports/mouseprint.org"),
    ("StarKist", "Chunk White Albacore", "canned goods", 5.0, 4.5, "oz", 1.99, 2.29, 2022, "Consumer Reports"),
    ("Bumble Bee", "Chunk Light Tuna", "canned goods", 5.0, 4.5, "oz", 1.29, 1.49, 2022, "Consumer Reports"),
    ("Bumble Bee", "Solid White Albacore", "canned goods", 5.0, 4.5, "oz", 2.29, 2.49, 2022, "Consumer Reports"),
    ("Chicken of the Sea", "Chunk Light Tuna", "canned goods", 5.0, 4.5, "oz", 1.19, 1.39, 2022, "r/shrinkflation"),
    ("Del Monte", "Peach Slices", "canned goods", 15.25, 14.5, "oz", 2.29, 2.49, 2023, "r/shrinkflation"),
    ("Del Monte", "Fruit Cocktail", "canned goods", 15.25, 14.5, "oz", 2.29, 2.49, 2023, "r/shrinkflation"),
    ("Dole", "Pineapple Chunks in Juice", "canned goods", 20.0, 18.0, "oz", 2.49, 2.79, 2023, "r/shrinkflation"),
    ("Green Giant", "Cut Green Beans", "canned goods", 14.5, 13.0, "oz", 1.29, 1.49, 2023, "r/shrinkflation"),
    ("Green Giant", "Whole Kernel Corn", "canned goods", 15.25, 14.0, "oz", 1.29, 1.49, 2023, "r/shrinkflation"),
    ("Bush's", "Original Baked Beans", "canned goods", 28.0, 24.0, "oz", 3.29, 3.49, 2023, "r/shrinkflation"),
    ("Hormel", "Chili with Beans", "canned goods", 15.0, 14.0, "oz", 2.99, 3.29, 2023, "r/shrinkflation"),
    ("Chef Boyardee", "Beefaroni", "canned goods", 15.0, 14.5, "oz", 1.49, 1.79, 2023, "r/shrinkflation"),
    ("Ro-Tel", "Original Diced Tomatoes & Green Chilies", "canned goods", 10.0, 9.0, "oz", 1.49, 1.69, 2023, "r/shrinkflation"),
    ("Hunts", "Tomato Sauce", "canned goods", 15.0, 14.5, "oz", 1.29, 1.49, 2022, "r/shrinkflation"),

    # ================================================================
    # PERSONAL CARE — shampoo, body wash, deodorant, skincare
    # ================================================================
    ("Dove", "Deep Moisture Body Wash", "personal care", 22.0, 20.0, "fl oz", 6.99, 7.49, 2023, "r/shrinkflation"),
    ("Dove", "Sensitive Skin Body Wash", "personal care", 22.0, 20.0, "fl oz", 6.99, 7.49, 2023, "r/shrinkflation"),
    ("Dove", "Men+Care Clean Comfort Body Wash", "personal care", 18.0, 16.0, "fl oz", 6.99, 7.49, 2023, "r/shrinkflation"),
    ("Dove", "Invisible Solid Deodorant", "personal care", 2.6, 2.4, "oz", 5.49, 5.99, 2023, "r/shrinkflation"),
    ("Old Spice", "High Endurance Deodorant", "personal care", 3.0, 2.6, "oz", 5.49, 5.99, 2022, "r/shrinkflation"),
    ("Old Spice", "Swagger Body Wash", "personal care", 21.0, 18.0, "fl oz", 6.99, 7.49, 2023, "r/shrinkflation"),
    ("Secret", "Outlast Clear Gel Deodorant", "personal care", 2.6, 2.4, "oz", 6.49, 6.99, 2023, "r/shrinkflation"),
    ("Degree", "UltraClear Deodorant", "personal care", 2.7, 2.6, "oz", 5.99, 6.49, 2023, "r/shrinkflation"),
    ("Pantene", "Pro-V Daily Moisture Renewal Shampoo", "personal care", 25.4, 22.0, "fl oz", 6.99, 7.49, 2023, "r/shrinkflation"),
    ("Pantene", "Pro-V Conditioner", "personal care", 25.4, 22.0, "fl oz", 6.99, 7.49, 2023, "r/shrinkflation"),
    ("Head & Shoulders", "Classic Clean Shampoo", "personal care", 23.7, 21.9, "fl oz", 7.49, 7.99, 2022, "r/shrinkflation"),
    ("Head & Shoulders", "Old Spice 2-in-1", "personal care", 21.9, 20.0, "fl oz", 7.99, 8.49, 2023, "r/shrinkflation"),
    ("Suave", "Essentials Daily Clarifying Shampoo", "personal care", 30.0, 22.5, "fl oz", 3.49, 3.49, 2022, "r/shrinkflation"),
    ("TRESemme", "Smooth & Silky Shampoo", "personal care", 28.0, 22.0, "fl oz", 5.99, 5.99, 2022, "r/shrinkflation"),
    ("Herbal Essences", "Argan Oil Shampoo", "personal care", 13.5, 11.7, "fl oz", 5.99, 6.49, 2023, "r/shrinkflation"),
    ("Olay", "Regenerist Moisturizer", "personal care", 1.7, 1.5, "oz", 28.99, 29.99, 2023, "r/shrinkflation"),
    ("Jergens", "Ultra Healing Lotion", "personal care", 21.0, 16.8, "fl oz", 6.99, 6.99, 2022, "r/shrinkflation"),
    ("Cetaphil", "Daily Facial Cleanser", "personal care", 16.0, 14.0, "fl oz", 12.99, 13.49, 2023, "r/shrinkflation"),
    ("Aveeno", "Daily Moisturizing Lotion", "personal care", 18.0, 16.0, "fl oz", 10.99, 11.49, 2023, "r/shrinkflation"),
    ("Neutrogena", "Oil-Free Acne Wash", "personal care", 9.1, 8.0, "fl oz", 8.99, 9.49, 2023, "r/shrinkflation"),
    ("CeraVe", "Moisturizing Cream", "personal care", 19.0, 16.0, "oz", 17.99, 18.99, 2023, "r/shrinkflation"),
    ("Dial", "Spring Water Body Wash", "personal care", 21.0, 16.0, "fl oz", 4.99, 4.99, 2022, "r/shrinkflation"),
    ("Softsoap", "Moisturizing Body Wash", "personal care", 20.0, 18.0, "fl oz", 4.99, 5.29, 2023, "r/shrinkflation"),
    ("Vaseline", "Intensive Care Lotion", "personal care", 24.5, 20.3, "fl oz", 7.99, 7.99, 2022, "r/shrinkflation"),
    ("Ban", "Roll-On Deodorant", "personal care", 3.5, 2.5, "fl oz", 4.99, 5.29, 2023, "r/shrinkflation"),

    # ================================================================
    # SNACK BARS / GRANOLA BARS / PROTEIN BARS
    # ================================================================
    ("Nature Valley", "Crunchy Oats 'n Honey (6-pack)", "snack bars", 8.94, 7.44, "oz", 3.99, 4.29, 2022, "Consumer Reports"),
    ("Nature Valley", "Sweet & Salty Nut Peanut", "snack bars", 7.4, 6.2, "oz", 3.99, 4.49, 2023, "r/shrinkflation"),
    ("Nature Valley", "Protein Peanut Butter Dark Chocolate", "snack bars", 8.94, 7.44, "oz", 4.49, 4.99, 2023, "r/shrinkflation"),
    ("KIND", "Dark Chocolate Nuts & Sea Salt", "snack bars", 1.4, 1.2, "oz each", 1.49, 1.69, 2022, "r/shrinkflation"),
    ("KIND", "Peanut Butter Dark Chocolate", "snack bars", 1.4, 1.2, "oz each", 1.49, 1.69, 2022, "r/shrinkflation"),
    ("Clif Bar", "Chocolate Chip", "snack bars", 2.4, 2.28, "oz", 1.69, 1.89, 2023, "r/shrinkflation"),
    ("Clif Bar", "Crunchy Peanut Butter", "snack bars", 2.4, 2.28, "oz", 1.69, 1.89, 2023, "r/shrinkflation"),
    ("RXBAR", "Chocolate Sea Salt", "snack bars", 1.83, 1.73, "oz", 2.49, 2.79, 2023, "r/shrinkflation"),
    ("Quest", "Chocolate Chip Cookie Dough Protein Bar", "snack bars", 2.12, 1.94, "oz", 2.79, 2.99, 2023, "r/shrinkflation"),
    ("Quaker", "Chewy Granola Bar Chocolate Chip (8-pack)", "snack bars", 6.72, 6.0, "oz", 3.49, 3.79, 2022, "mouseprint.org"),
    ("Quaker", "Chewy Dipps Chocolate Chip", "snack bars", 6.7, 5.86, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Fiber One", "90 Calorie Chocolate Fudge Brownie", "snack bars", 5.34, 4.8, "oz", 3.99, 4.29, 2022, "r/shrinkflation"),
    ("Nutri-Grain", "Strawberry Cereal Bars (8-pack)", "snack bars", 10.4, 9.6, "oz", 4.29, 4.69, 2023, "r/shrinkflation"),
    ("Larabar", "Peanut Butter Chocolate Chip", "snack bars", 1.6, 1.5, "oz", 1.49, 1.69, 2023, "r/shrinkflation"),
    ("Luna Bar", "Lemonzest", "snack bars", 1.69, 1.52, "oz", 1.49, 1.69, 2023, "r/shrinkflation"),
    ("Special K", "Pastry Crisps Strawberry", "snack bars", 4.4, 3.96, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Kashi", "Honey Almond Flax Chewy Bar", "snack bars", 7.4, 6.5, "oz", 4.29, 4.69, 2023, "r/shrinkflation"),
    ("PowerBar", "Performance Energy Chocolate", "snack bars", 2.29, 2.03, "oz", 1.99, 2.29, 2023, "r/shrinkflation"),
    ("That's It", "Apple + Mango Bar", "snack bars", 1.2, 1.05, "oz", 1.49, 1.69, 2023, "r/shrinkflation"),
    ("Belvita", "Blueberry Breakfast Biscuits", "snack bars", 8.8, 7.76, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),

    # ================================================================
    # SAUCES & DRESSINGS
    # ================================================================
    ("Ragu", "Traditional Pasta Sauce", "sauces", 24.0, 22.0, "oz", 3.29, 3.49, 2023, "r/shrinkflation"),
    ("Ragu", "Chunky Mushroom & Green Pepper", "sauces", 24.0, 22.0, "oz", 3.29, 3.49, 2023, "r/shrinkflation"),
    ("Prego", "Traditional Italian Sauce", "sauces", 24.0, 23.5, "oz", 3.49, 3.79, 2022, "mouseprint.org"),
    ("Prego", "Marinara", "sauces", 24.0, 23.5, "oz", 3.49, 3.79, 2022, "mouseprint.org"),
    ("Classico", "Tomato & Basil Pasta Sauce", "sauces", 24.0, 22.0, "oz", 3.79, 3.99, 2023, "r/shrinkflation"),
    ("Newman's Own", "Marinara", "sauces", 24.0, 22.0, "oz", 4.29, 4.49, 2023, "r/shrinkflation"),
    ("Bertolli", "Tomato & Basil", "sauces", 24.0, 22.0, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Kraft", "Original BBQ Sauce", "sauces", 18.0, 16.0, "oz", 2.49, 2.79, 2023, "r/shrinkflation"),
    ("Sweet Baby Ray's", "Original BBQ Sauce", "sauces", 28.0, 24.0, "oz", 3.29, 3.49, 2023, "r/shrinkflation"),
    ("Stubb's", "Original BBQ Sauce", "sauces", 18.0, 15.0, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Ken's", "Steakhouse Ranch Dressing", "sauces", 16.0, 14.5, "oz", 3.49, 3.79, 2023, "r/shrinkflation"),
    ("Wish-Bone", "Italian Dressing", "sauces", 16.0, 15.0, "oz", 3.29, 3.49, 2022, "r/shrinkflation"),
    ("Kraft", "Thousand Island Dressing", "sauces", 16.0, 14.0, "oz", 3.49, 3.79, 2023, "r/shrinkflation"),
    ("Newman's Own", "Balsamic Vinaigrette", "sauces", 16.0, 14.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Tabasco", "Original Red Pepper Sauce", "sauces", 5.0, 4.0, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Frank's RedHot", "Original", "sauces", 12.0, 10.0, "oz", 3.49, 3.79, 2023, "r/shrinkflation"),
    ("Sriracha", "Huy Fong Hot Chili Sauce", "sauces", 17.0, 14.0, "oz", 3.99, 4.99, 2023, "r/shrinkflation"),
    ("A1", "Steak Sauce", "sauces", 10.0, 8.0, "oz", 4.99, 5.29, 2023, "r/shrinkflation"),
    ("Kikkoman", "Soy Sauce", "sauces", 15.0, 13.5, "oz", 3.29, 3.49, 2023, "r/shrinkflation"),
    ("Pace", "Chunky Salsa Medium", "sauces", 24.0, 22.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Tostitos", "Salsa Con Queso", "sauces", 15.0, 13.0, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),

    # ================================================================
    # BAKING SUPPLIES
    # ================================================================
    ("Gold Medal", "All-Purpose Flour", "baking", 10.0, 8.0, "lb", 5.49, 5.99, 2023, "r/shrinkflation"),
    ("Gold Medal", "Self-Rising Flour", "baking", 5.0, 4.0, "lb", 3.49, 3.79, 2023, "r/shrinkflation"),
    ("Domino", "Granulated Sugar", "baking", 5.0, 4.0, "lb", 4.49, 4.49, 2023, "r/shrinkflation"),
    ("C&H", "Pure Cane Sugar", "baking", 5.0, 4.0, "lb", 4.49, 4.49, 2023, "r/shrinkflation"),
    ("Pillsbury", "All-Purpose Flour", "baking", 10.0, 8.0, "lb", 5.29, 5.79, 2023, "r/shrinkflation"),
    ("Betty Crocker", "Super Moist Cake Mix", "baking", 15.25, 13.25, "oz", 1.79, 1.99, 2022, "mouseprint.org"),
    ("Betty Crocker", "Brownie Mix Family Size", "baking", 18.3, 16.0, "oz", 2.49, 2.79, 2023, "r/shrinkflation"),
    ("Duncan Hines", "Classic Yellow Cake Mix", "baking", 15.25, 14.25, "oz", 1.79, 1.99, 2022, "r/shrinkflation"),
    ("Duncan Hines", "Brownie Mix", "baking", 18.3, 15.25, "oz", 2.29, 2.49, 2023, "r/shrinkflation"),
    ("Nestle", "Toll House Semi-Sweet Morsels", "baking", 12.0, 10.0, "oz", 3.99, 4.29, 2022, "Consumer Reports"),
    ("Nestle", "Toll House Dark Chocolate Morsels", "baking", 10.0, 9.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Hershey's", "Semi-Sweet Chocolate Chips", "baking", 12.0, 10.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Crisco", "Vegetable Shortening", "baking", 48.0, 40.0, "oz", 5.99, 6.49, 2023, "r/shrinkflation"),
    ("Pillsbury", "Crescent Rolls (8-count)", "baking", 8.0, 7.3, "oz", 2.99, 3.29, 2023, "r/shrinkflation"),
    ("Jell-O", "Instant Pudding Chocolate", "baking", 3.9, 3.4, "oz", 1.29, 1.49, 2023, "r/shrinkflation"),
    ("Cool Whip", "Original Whipped Topping", "baking", 8.0, 7.0, "oz", 2.49, 2.79, 2022, "r/shrinkflation"),
    ("Philadelphia", "Cream Cheese Block", "baking", 8.0, 7.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),

    # ================================================================
    # MEAT & DELI
    # ================================================================
    ("Oscar Mayer", "Bologna", "meat", 16.0, 14.0, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Oscar Mayer", "Turkey Breast Deli Meat", "meat", 9.0, 8.0, "oz", 5.49, 5.99, 2022, "mouseprint.org"),
    ("Oscar Mayer", "Wieners (10-pack)", "meat", 16.0, 14.0, "oz", 4.29, 4.59, 2023, "r/shrinkflation"),
    ("Hillshire Farm", "Ultra Thin Oven Roasted Turkey", "meat", 9.0, 7.0, "oz", 5.99, 6.49, 2022, "Consumer Reports"),
    ("Hillshire Farm", "Ultra Thin Honey Ham", "meat", 9.0, 7.0, "oz", 5.99, 6.49, 2022, "Consumer Reports"),
    ("Hillshire Farm", "Lit'l Smokies", "meat", 14.0, 12.0, "oz", 4.99, 5.29, 2023, "r/shrinkflation"),
    ("Land O'Frost", "Premium Turkey Breast", "meat", 16.0, 14.0, "oz", 5.99, 6.29, 2023, "r/shrinkflation"),
    ("Buddig", "Original Turkey", "meat", 2.5, 2.0, "oz", 1.49, 1.49, 2023, "r/shrinkflation"),
    ("Hebrew National", "Beef Franks (7-count)", "meat", 12.0, 11.0, "oz", 5.99, 6.29, 2023, "r/shrinkflation"),
    ("Ball Park", "Beef Franks (8-pack)", "meat", 15.0, 14.0, "oz", 4.99, 5.29, 2022, "r/shrinkflation"),
    ("Nathan's", "Skinless Beef Franks (8-pack)", "meat", 14.0, 12.0, "oz", 5.99, 6.29, 2023, "r/shrinkflation"),
    ("Hormel", "Black Label Bacon", "meat", 16.0, 12.0, "oz", 6.99, 7.49, 2022, "Consumer Reports"),
    ("Wright Brand", "Hickory Smoked Bacon", "meat", 24.0, 22.0, "oz", 10.99, 11.49, 2023, "r/shrinkflation"),
    ("Jimmy Dean", "Premium Pork Sausage Roll", "meat", 16.0, 14.0, "oz", 5.49, 5.79, 2023, "r/shrinkflation"),
    ("Spam", "Classic", "meat", 12.0, 11.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Tyson", "Chicken Nuggets (bag)", "meat", 32.0, 28.0, "oz", 8.99, 9.49, 2023, "r/shrinkflation"),
    ("Perdue", "Short Cuts Grilled Chicken", "meat", 9.0, 8.0, "oz", 5.49, 5.99, 2023, "r/shrinkflation"),

    # ================================================================
    # PET FOOD
    # ================================================================
    ("Purina", "Dog Chow Complete Adult", "pet food", 18.5, 16.5, "lb", 17.99, 18.99, 2023, "r/shrinkflation"),
    ("Purina", "Cat Chow Complete", "pet food", 16.0, 15.0, "lb", 15.99, 16.49, 2023, "r/shrinkflation"),
    ("Purina", "ONE SmartBlend Adult", "pet food", 16.5, 14.0, "lb", 22.99, 23.99, 2022, "r/shrinkflation"),
    ("Purina", "Friskies Pate (cans)", "pet food", 5.5, 5.0, "oz", 0.79, 0.89, 2023, "r/shrinkflation"),
    ("Iams", "Proactive Health Adult", "pet food", 15.0, 13.5, "lb", 19.99, 20.99, 2022, "r/shrinkflation"),
    ("Iams", "ProActive Health Indoor Cat", "pet food", 16.0, 14.0, "lb", 18.99, 19.99, 2023, "r/shrinkflation"),
    ("Pedigree", "Complete Nutrition Adult", "pet food", 18.0, 16.0, "lb", 15.99, 16.99, 2023, "r/shrinkflation"),
    ("Blue Buffalo", "Life Protection Adult", "pet food", 15.0, 13.0, "lb", 32.99, 34.99, 2023, "r/shrinkflation"),
    ("Meow Mix", "Original Choice", "pet food", 16.0, 13.5, "lb", 13.99, 14.99, 2023, "r/shrinkflation"),
    ("Rachael Ray Nutrish", "Real Chicken & Veggies", "pet food", 14.0, 12.0, "lb", 19.99, 21.99, 2023, "r/shrinkflation"),
    # Removed: Fancy Feast 3→2.8oz — can sizes are standardized, not well-documented
    ("Milk-Bone", "Original Dog Biscuits", "pet food", 24.0, 22.0, "oz", 5.49, 5.99, 2023, "r/shrinkflation"),
    ("Greenies", "Original Dental Dog Treats", "pet food", 12.0, 10.0, "oz", 12.99, 13.99, 2023, "r/shrinkflation"),
    ("Temptations", "Classic Cat Treats Chicken", "pet food", 6.3, 5.5, "oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Beggin'", "Strips Bacon Flavor", "pet food", 6.0, 5.0, "oz", 4.99, 5.29, 2023, "r/shrinkflation"),

    # ================================================================
    # BABY PRODUCTS
    # ================================================================
    ("Pampers", "Swaddlers (Size 1)", "baby", 198.0, 184.0, "count", 49.99, 52.99, 2022, "Consumer Reports"),
    ("Pampers", "Baby Dry (Size 3)", "baby", 144.0, 128.0, "count", 39.99, 41.99, 2023, "r/shrinkflation"),
    ("Pampers", "Sensitive Wipes (9-pack)", "baby", 576.0, 504.0, "count", 19.99, 20.99, 2023, "r/shrinkflation"),
    ("Huggies", "Little Snugglers (Size 1)", "baby", 198.0, 180.0, "count", 47.99, 49.99, 2022, "r/shrinkflation"),
    ("Huggies", "Little Movers (Size 4)", "baby", 120.0, 108.0, "count", 39.99, 41.99, 2023, "r/shrinkflation"),
    ("Huggies", "Natural Care Wipes (10-pack)", "baby", 560.0, 480.0, "count", 18.99, 19.99, 2023, "r/shrinkflation"),
    ("Luvs", "Ultra Leakguards (Size 2)", "baby", 148.0, 132.0, "count", 24.99, 26.49, 2023, "r/shrinkflation"),
    ("Enfamil", "NeuroPro Infant Formula", "baby", 20.7, 19.5, "oz", 37.99, 39.99, 2022, "r/shrinkflation"),
    ("Similac", "Advance Infant Formula", "baby", 23.2, 20.6, "oz", 34.99, 36.99, 2022, "r/shrinkflation"),
    ("Gerber", "Puffs Cereal Snack", "baby", 1.48, 1.35, "oz", 2.99, 3.19, 2023, "r/shrinkflation"),
    ("Gerber", "2nd Foods Baby Food", "baby", 4.0, 3.5, "oz each", 1.39, 1.59, 2023, "r/shrinkflation"),
    ("Earth's Best", "Organic Baby Food Pouches", "baby", 4.0, 3.5, "oz", 1.79, 1.99, 2023, "r/shrinkflation"),

    # ================================================================
    # CLEANING PRODUCTS
    # ================================================================
    ("Lysol", "Disinfectant Spray Original", "cleaning", 19.0, 16.0, "oz", 6.49, 6.99, 2022, "r/shrinkflation"),
    ("Lysol", "Disinfecting Wipes (80-count)", "cleaning", 80.0, 75.0, "count", 5.99, 6.29, 2023, "r/shrinkflation"),
    ("Clorox", "Disinfecting Wipes (75-count)", "cleaning", 75.0, 70.0, "count", 5.49, 5.99, 2022, "r/shrinkflation"),
    ("Clorox", "Clean-Up Cleaner + Bleach", "cleaning", 32.0, 28.0, "fl oz", 4.99, 5.29, 2023, "r/shrinkflation"),
    ("Windex", "Original Glass Cleaner", "cleaning", 26.0, 23.0, "fl oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Method", "All-Purpose Cleaner", "cleaning", 28.0, 25.0, "fl oz", 4.49, 4.79, 2023, "r/shrinkflation"),
    ("Pine-Sol", "Original Multi-Surface Cleaner", "cleaning", 48.0, 40.0, "fl oz", 5.49, 5.79, 2022, "r/shrinkflation"),
    ("Mr. Clean", "Multi-Surface Cleaner", "cleaning", 45.0, 40.0, "fl oz", 4.99, 5.29, 2023, "r/shrinkflation"),
    ("Swiffer", "WetJet Refill Pads", "cleaning", 24.0, 20.0, "count", 9.99, 10.49, 2023, "r/shrinkflation"),
    ("Swiffer", "WetJet Solution Refill", "cleaning", 42.2, 38.0, "fl oz", 7.99, 8.49, 2023, "r/shrinkflation"),
    ("Febreze", "Air Freshener Spray", "cleaning", 8.8, 7.5, "oz", 5.49, 5.79, 2023, "r/shrinkflation"),
    ("OxiClean", "Versatile Stain Remover", "cleaning", 5.0, 3.5, "lb", 12.99, 13.49, 2023, "r/shrinkflation"),
    # Scrub Daddy removed — count stays 3→3, that's inflation not shrinkflation
    ("Pledge", "Multi-Surface Cleaner Spray", "cleaning", 14.2, 12.5, "oz", 5.49, 5.99, 2023, "r/shrinkflation"),
    ("Ajax", "Ultra Dish Liquid", "cleaning", 28.0, 22.0, "fl oz", 2.99, 2.99, 2022, "r/shrinkflation"),

    # ================================================================
    # SPICES & SEASONINGS
    # ================================================================
    ("McCormick", "Ground Cinnamon", "spices", 4.12, 3.5, "oz", 5.99, 6.49, 2023, "r/shrinkflation"),
    ("McCormick", "Black Pepper Ground", "spices", 6.0, 5.0, "oz", 8.99, 9.49, 2022, "mouseprint.org"),
    ("McCormick", "Garlic Powder", "spices", 5.25, 4.5, "oz", 6.49, 6.99, 2023, "r/shrinkflation"),
    ("McCormick", "Onion Powder", "spices", 4.5, 3.75, "oz", 5.99, 6.49, 2023, "r/shrinkflation"),
    ("McCormick", "Chili Powder", "spices", 4.5, 3.75, "oz", 5.99, 6.49, 2023, "r/shrinkflation"),
    ("McCormick", "Taco Seasoning Mix", "spices", 1.25, 1.0, "oz", 1.29, 1.49, 2022, "mouseprint.org"),
    ("McCormick", "Italian Seasoning", "spices", 1.5, 1.25, "oz", 4.99, 5.49, 2023, "r/shrinkflation"),
    ("Lawry's", "Seasoned Salt", "spices", 16.0, 12.0, "oz", 5.49, 5.99, 2023, "r/shrinkflation"),
    ("Mrs. Dash", "Original Seasoning Blend", "spices", 6.75, 6.0, "oz", 5.49, 5.79, 2023, "r/shrinkflation"),
    ("Tony Chachere's", "Creole Seasoning", "spices", 8.0, 6.75, "oz", 3.49, 3.79, 2023, "r/shrinkflation"),
    ("Old Bay", "Seasoning", "spices", 6.0, 5.0, "oz", 5.49, 5.99, 2023, "r/shrinkflation"),

    # ================================================================
    # BREAKFAST — pancake mix, syrup, oatmeal
    # ================================================================
    ("Quaker", "Instant Oatmeal Original (12-pack)", "breakfast", 11.8, 9.8, "oz", 4.49, 4.79, 2022, "BLS"),
    ("Quaker", "Instant Oatmeal Maple Brown Sugar (10-pack)", "breakfast", 15.1, 12.1, "oz", 4.49, 4.79, 2022, "BLS"),
    ("Quaker", "Old Fashioned Oats", "breakfast", 42.0, 38.0, "oz", 5.49, 5.79, 2023, "r/shrinkflation"),
    ("Aunt Jemima/Pearl Milling Co.", "Original Pancake Mix", "breakfast", 32.0, 28.0, "oz", 3.49, 3.79, 2022, "r/shrinkflation"),
    ("Aunt Jemima/Pearl Milling Co.", "Original Syrup", "breakfast", 24.0, 20.0, "fl oz", 4.49, 4.79, 2022, "r/shrinkflation"),
    ("Bisquick", "Original Pancake & Baking Mix", "breakfast", 40.0, 36.0, "oz", 4.49, 4.99, 2023, "r/shrinkflation"),
    ("Mrs. Butterworth's", "Original Syrup", "breakfast", 24.0, 20.0, "fl oz", 4.49, 4.79, 2022, "r/shrinkflation"),
    ("Log Cabin", "Original Syrup", "breakfast", 24.0, 22.0, "fl oz", 4.29, 4.59, 2023, "r/shrinkflation"),
    ("Krusteaz", "Buttermilk Pancake Mix", "breakfast", 32.0, 28.0, "oz", 3.99, 4.29, 2023, "r/shrinkflation"),
    ("Carnation", "Breakfast Essentials Powder", "breakfast", 17.7, 14.84, "oz", 6.99, 7.49, 2023, "r/shrinkflation"),
    ("Pop-Tarts", "Frosted Strawberry (8-count)", "breakfast", 14.7, 13.5, "oz", 3.99, 4.29, 2022, "mouseprint.org"),
    ("Pop-Tarts", "Frosted Brown Sugar Cinnamon (8-count)", "breakfast", 14.0, 13.0, "oz", 3.99, 4.29, 2022, "mouseprint.org"),

    # ================================================================
    # DRINKS — soda, energy, water
    # ================================================================
    # Removed: Coca-Cola/Pepsi/Dr Pepper/Sprite/Mountain Dew 20→16.9oz — new SKU alongside existing, not replacement
    # Removed: Monster Energy 16→15oz — not well-documented
    # Removed: Red Bull 12→8.4oz — FAKE, 8.4oz has always been the standard size
    # Removed: Celsius 16→12oz — two different SKUs confused
    ("Body Armor", "SuperDrink Strawberry Banana", "drinks", 28.0, 24.0, "fl oz", 2.49, 2.49, 2023, "r/shrinkflation"),
    ("Poland Spring", "Sport Cap (6-pack)", "drinks", 23.7, 20.0, "fl oz each", 4.99, 4.99, 2022, "r/shrinkflation"),
    ("Nestle Pure Life", "Purified Water (24-pack)", "drinks", 16.9, 16.0, "fl oz each", 3.99, 3.99, 2022, "r/shrinkflation"),
    ("Kool-Aid", "Jammers Grape (10-pack)", "drinks", 6.0, 5.0, "fl oz each", 3.49, 3.49, 2023, "r/shrinkflation"),
    ("Capri Sun", "Pacific Cooler (10-pack)", "drinks", 6.0, 5.0, "fl oz each", 3.99, 3.99, 2023, "r/shrinkflation"),
]
# fmt: on


# ================================================================
# STABLE PRODUCTS — no shrinkflation, for comparison baseline
# ================================================================
# fmt: off
STABLE_PRODUCTS = [
    # Ice cream
    ("Halo Top", "Vanilla Bean", "ice cream", 16.0, "fl oz", 4.99),
    ("So Delicious", "Cashew Milk Vanilla", "ice cream", 16.0, "fl oz", 5.49),
    ("Magnum", "Double Caramel", "ice cream", 3.0, "fl oz", 4.99),
    ("Jeni's", "Brambleberry Crisp", "ice cream", 16.0, "fl oz", 12.99),
    ("McConnell's", "Eureka Lemon", "ice cream", 14.0, "fl oz", 11.99),
    # Chips
    ("Utz", "Kettle Classics Original", "chips", 8.0, "oz", 3.99),
    ("Herr's", "Original Chips", "chips", 8.0, "oz", 3.79),
    ("Terra", "Original Vegetable Chips", "chips", 5.0, "oz", 4.29),
    ("Boulder Canyon", "Classic Avocado Oil Chips", "chips", 5.25, "oz", 4.49),
    ("Popchips", "Sea Salt", "chips", 5.0, "oz", 3.99),
    ("Siete", "Sea Salt Tortilla Chips", "chips", 5.0, "oz", 4.49),
    # Cereal
    ("Nature's Path", "Organic Heritage Flakes", "cereal", 13.25, "oz", 5.49),
    ("Cascadian Farm", "Organic Granola", "cereal", 16.0, "oz", 5.99),
    ("Kashi", "GoLean Original", "cereal", 13.1, "oz", 5.29),
    ("Magic Spoon", "Cocoa", "cereal", 7.0, "oz", 9.99),
    ("Three Wishes", "Cinnamon", "cereal", 8.6, "oz", 7.99),
    ("Barbara's", "Puffins Original", "cereal", 10.0, "oz", 4.99),
    ("Bear Naked", "Granola Vanilla Almond", "cereal", 12.0, "oz", 5.99),
    # Beverages
    ("V8", "Original Vegetable Juice", "beverages", 46.0, "fl oz", 3.99),
    ("Mott's", "Apple Juice", "beverages", 64.0, "fl oz", 3.79),
    ("Welch's", "Grape Juice", "beverages", 64.0, "fl oz", 4.49),
    ("Naked", "Green Machine", "beverages", 15.2, "fl oz", 4.29),
    ("Honest", "Organic Honey Green Tea", "beverages", 16.9, "fl oz", 2.49),
    # Coffee
    ("Lavazza", "Super Crema", "coffee", 35.2, "oz", 18.99),
    ("Illy", "Classico Ground", "coffee", 8.8, "oz", 10.99),
    ("Green Mountain", "Nantucket Blend K-Cups (12-ct)", "coffee", 12.0, "count", 9.99),
    ("Death Wish", "Ground Coffee", "coffee", 16.0, "oz", 19.99),
    ("Community Coffee", "Breakfast Blend", "coffee", 12.0, "oz", 7.99),
    ("Stumptown", "Hair Bender Whole Bean", "coffee", 12.0, "oz", 14.99),
    # Cookies & Crackers
    ("Tate's", "Chocolate Chip Cookies", "cookies", 7.0, "oz", 5.99),
    ("Famous Amos", "Chocolate Chip (small)", "cookies", 3.0, "oz", 1.49),
    ("Annie's", "Cheddar Bunnies", "crackers", 7.5, "oz", 3.99),
    ("Mary's Gone", "Original Crackers", "crackers", 6.5, "oz", 5.49),
    ("Simple Mills", "Almond Flour Crackers", "crackers", 4.25, "oz", 4.99),
    ("Back to Nature", "Classic Round Crackers", "crackers", 8.5, "oz", 3.99),
    # Yogurt
    ("Stonyfield", "Organic Vanilla (tub)", "yogurt", 32.0, "oz", 5.49),
    ("Wallaby", "Organic Greek Vanilla", "yogurt", 5.3, "oz", 1.99),
    ("Nancy's", "Organic Whole Milk Yogurt", "yogurt", 32.0, "oz", 5.99),
    ("Maple Hill", "Grass-Fed Vanilla", "yogurt", 5.3, "oz", 2.29),
    # Condiments
    ("Sir Kensington's", "Classic Ketchup", "condiments", 20.0, "oz", 4.99),
    ("Primal Kitchen", "Avocado Oil Mayo", "condiments", 12.0, "fl oz", 8.99),
    ("Duke's", "Real Mayonnaise", "condiments", 32.0, "fl oz", 4.99),
    ("Annie's", "Organic Ketchup", "condiments", 24.0, "oz", 4.49),
    ("Tessemae's", "Organic Ranch", "condiments", 10.0, "fl oz", 5.99),
    # Cheese
    ("Organic Valley", "Sharp Cheddar", "cheese", 8.0, "oz", 5.99),
    ("Kerrygold", "Dubliner", "cheese", 7.0, "oz", 5.49),
    ("Cabot", "Extra Sharp Cheddar", "cheese", 8.0, "oz", 4.99),
    # Bread
    ("Wonder", "Classic White", "bread", 20.0, "oz", 3.49),
    ("Oroweat", "Whole Grains 100% Whole Wheat", "bread", 24.0, "oz", 5.49),
    ("Franz", "Big Horn Wheat", "bread", 24.0, "oz", 4.99),
    # Pasta
    ("San Giorgio", "Spaghetti", "pasta", 16.0, "oz", 1.49),
    ("Banza", "Chickpea Penne", "pasta", 8.0, "oz", 3.49),
    ("DeLallo", "Organic Whole Wheat Penne", "pasta", 16.0, "oz", 2.99),
    # Candy
    ("Ghirardelli", "Dark Chocolate Squares", "candy", 5.32, "oz", 4.99),
    ("Lindt", "Lindor Milk Chocolate Truffles", "candy", 5.1, "oz", 5.49),
    ("Tony's Chocolonely", "Milk Chocolate", "candy", 6.35, "oz", 4.99),
    # Household
    ("Seventh Generation", "Dish Liquid", "household", 19.0, "fl oz", 3.99),
    ("Method", "Dish Soap", "household", 18.0, "fl oz", 3.99),
    ("Mrs. Meyer's", "Hand Soap Lavender", "household", 12.5, "fl oz", 4.49),
    ("ECOS", "Laundry Detergent", "household", 100.0, "fl oz", 11.99),
    # Frozen food
    ("Amy's", "Cheese Pizza", "frozen food", 13.0, "oz", 8.99),
    ("Saffron Road", "Chicken Pad Thai", "frozen food", 10.0, "oz", 5.49),
    ("Evol", "Chicken Burrito", "frozen food", 6.0, "oz", 3.99),
    # Personal care
    ("Dr. Bronner's", "Pure-Castile Soap Peppermint", "personal care", 32.0, "fl oz", 15.99),
    ("Burt's Bees", "Lip Balm Original", "personal care", 0.15, "oz", 3.49),
    # Pet food
    ("Taste of the Wild", "High Prairie Adult", "pet food", 28.0, "lb", 49.99),
    ("Wellness", "Complete Health Adult", "pet food", 15.0, "lb", 34.99),
    # Baby
    ("Babyganics", "Diapers (Size 3)", "baby", 160.0, "count", 44.99),
    ("Honest Company", "Diapers (Size 2)", "baby", 128.0, "count", 39.99),
    # Snack bars
    ("RXBAR", "Peanut Butter", "snack bars", 1.83, "oz", 2.49),
    ("Epic", "Bison Bacon Bar", "snack bars", 1.3, "oz", 2.99),
    # Canned goods
    ("Wild Planet", "Wild Albacore Tuna", "canned goods", 5.0, "oz", 3.99),
    ("Muir Glen", "Organic Tomato Sauce", "canned goods", 15.0, "oz", 2.49),
    # Sauces
    ("Rao's", "Homemade Marinara", "sauces", 24.0, "oz", 8.99),
    ("Primal Kitchen", "Organic Ketchup", "sauces", 11.3, "oz", 5.99),
    # Baking
    ("King Arthur", "All-Purpose Flour", "baking", 5.0, "lb", 5.49),
    ("Bob's Red Mill", "Old Fashioned Oats", "baking", 32.0, "oz", 5.99),
    # Cleaning
    ("Branch Basics", "Concentrate Cleaner", "cleaning", 33.0, "fl oz", 49.00),
    ("Blueland", "Multi-Surface Cleaner Kit", "cleaning", 1.0, "kit", 12.00),
]
# fmt: on


# 9 major US retailers where national brands are sold
RETAILERS = [
    "walmart",
    "kroger",
    "target",
    "costco",
    "safeway",
    "publix",
    "h-e-b",
    "meijer",
    "albertsons",
]
