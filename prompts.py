"""
LLM Prompts for the retail customer retention system.
All prompts use Python string formatting with named placeholders.
"""

DISCOUNT_MESSAGE_PROMPT = """
Based on the following session context, generate a discount message:

Session Context: {session_context}

Generate:
1) A title
2) A message

The message should:
- Offer a discount (5-15%) or incentive
- Be specific to a subcategory or article type
- Create urgency and encourage action
- Be concise and compelling
- Keep message under 90 characters if possible, or maximum 115 characters.

Output as JSON:
{{
    "title": "Brief attention-grabbing title",
    "message": "Specific discount message with subcategory/article type"
}}
"""

INTENT_INFERENCE_PROMPT = """
SEARCH BEHAVIOR ANALYSIS:

Latest Searches: {recent_focus}
Search Clusters: {search_clusters}

Intent Insights:
- Has size mentions: {has_size_mentions}
- Dominant topic dimension: {dominant_topic_dimension}
- Behavioral indicators: {behavioral_indicators}

TASK: Based on this analysis, determine the user's primary shopping intent.

Provide a concise intent summary that captures:
1. What specific product/category they're most likely seeking
2. Any inferred attributes (brand, size, style, occasion)
3. Shopping urgency level based on search patterns

Keep your response focused and actionable for product search.
Format as a clear search query that would find relevant products.

Example formats:
- "Women's running shoes, athletic footwear, Nike or Adidas preferred"
- "Formal dress shirts, business casual, medium to large sizes"
- "Wireless headphones, noise canceling, budget-conscious shopper"
"""

SOCIAL_PROOF_MESSAGE_PROMPT = """
You are a Marketing UX writer and want to create a compelling social proof message.
The customer showed a {severity} purchase intent based on the following evidence '{evidence}'.
{product_info}

Make it engaging and persuasive.

Output:
- An object with the following format: {{ "title": "", "message": "" }}
- title: short title for the social proof notification
- message: short description for the social proof notification, take the Product details provided and the evidence to tailor this.

The message should:
- Be concise and compelling
- Create urgency or social validation
- Encourage immediate action
- Should NOT include any discounts. But you can add analytics like amount of people interested in that category, etc...
<<<<<<< HEAD
- Keep message under 90 characters if possible, or maximum 115 characters.
=======
- Try to keep shorter than 25 words.
>>>>>>> 39b7b365a914a716c0c517576535999a8ad49aaf

The title should be:
- Short and attention-grabbing
- For example: "Popular Right Now", "Good Choice", "[The category] are moving"

Example output:
{{
    "title": "Popular pick!",
    "message": "Five customers completed a purchase in Shoes recently. You're looking in the right place."
}}
"""

PRODUCT_PRESSURE_MESSAGE_PROMPT = """
Generate a short, compelling pressure message to encourage purchase of a product.

The message should create urgency or social pressure such as:
- "X people purchased this in the last Y days"
- "This item is trending"  
- "Only few units left"
- "High demand item"
- "Popular choice this week"

Requirements:
- Keep it under 15 words
- Make it feel authentic and believable
- Create urgency without being pushy
- Don't mention specific numbers unless they sound realistic

Just return the message text, no JSON formatting needed.
"""