from mcp_server.server import mcp  # Import the single mcp instance shared across your project  
from mongo import get_db
from config import SESSION_STATE_COLLECTION, SESSION_SIGNALS_COLLECTION
import logging

@mcp.tool(
    name="get_session_search_history",
    description="Fetch search history (array of search query strings) for a session"
)
def get_session_search_history(uid: str, sid: str) -> list:
    logging.info("🔍 Fetching session search history...")
    
    db = get_db()
    query = {"userId": uid, "sessionId": sid}
    projection = {"_id": 1, "searchHistory": 1}
    
    logging.info("📊 Executing MongoDB query for session search history")
    
    doc = db[SESSION_STATE_COLLECTION].find_one(query, projection)
    if doc is None:
        logging.warning("⚠️ No session document found for requested session")
        return []
    
    search_history = doc.get("searchHistory", [])
    logging.info(f"✅ Retrieved search history: {len(search_history) if isinstance(search_history, list) else 0} queries")
    return search_history if isinstance(search_history, list) else []

@mcp.tool(
    name="get_session_signals",
    description="Fetch past behavioral signals for a session"
)
def get_session_signals(uid: str, sid: str) -> list:
    logging.info("🔍 Fetching session signals")
    
    db = get_db()
    query = {"uid": uid, "sid": sid, "signal": "search-friction"}
    
    signals_cursor = db[SESSION_SIGNALS_COLLECTION].find(query).sort("ts", -1)
    
    signals = []
    for doc in signals_cursor:
        # Convert MongoDB document to JSON-serializable dict
        json_doc = {}
        for key, value in doc.items():
            if key == '_id':
                json_doc[key] = str(value)  # Convert ObjectId to string
            elif hasattr(value, 'isoformat'):  # Handle datetime objects
                json_doc[key] = value.isoformat()
            elif isinstance(value, (dict, list, str, int, float, bool)) or value is None:
                json_doc[key] = value  # Already JSON-serializable
            else:
                json_doc[key] = str(value)  # Convert other types to string
        signals.append(json_doc)
    
    logging.info(f"🔍 Final signals list length: {len(signals)}")
    
    # Test JSON serializability to ensure MCP can handle the data
    try:
        import json
        json_test = json.dumps(signals)
        logging.info(f"✅ JSON serialization test passed - {len(json_test)} chars")
    except Exception as e:
        logging.error(f"❌ JSON serialization test failed: {e}")
        # If serialization fails, return empty list to avoid MCP issues
        return []
    
    logging.info(f"📤 Returning {len(signals)} signals from get_session_signals")
    return signals

@mcp.tool(
    name="analyze_session_intent_patterns",
    description="Analyze search patterns and behavioral signals to extract user intent insights"
)
def analyze_session_intent_patterns(search_history: list, past_signals: list) -> dict:
    """
    Algorithmic analysis of session data to extract intent patterns.
    
    Args:
        search_history: Array of search query strings 
        past_signals: Array of behavioral signal objects with topic.dimension, topic.value, and evidence
    
    Returns:
        Structured analysis with patterns, confidence levels, and recommendations
    """
    logging.info(f"🔍 Analyzing intent patterns for {len(search_history)} searches and {len(past_signals)} signals")
    
    analysis = {
        "search_clusters": [],
        "recent_focus": [], # what the user has searched in their session
        "recommended_search_query": "",
        "intent_insights": {}
    }
    
    try:
        # Clean and prepare search history
        clean_searches = [s.strip().lower() for s in search_history if s and s.strip()] if search_history else []
        
        # Extract signal insights even if no search history
        signal_insights = _extract_signal_insights(past_signals)
        
        # If we have neither searches nor signals, return minimal analysis
        if not clean_searches and not past_signals:
            logging.warning("⚠️ No search history or signals provided")
            return analysis
        
        # ANALYSIS 1: Semantic Clustering (combine searches and signals)
        analysis["search_clusters"] = _identify_search_clusters(clean_searches, signal_insights)
        
        # ANALYSIS 2: Recent Focus (searches or signal topics)
        if clean_searches and len(clean_searches) >= 3:
            analysis["recent_focus"] = clean_searches[-3:]
        elif clean_searches:
            analysis["recent_focus"] = clean_searches
        else:
            analysis["recent_focus"] = _extract_signal_focus(past_signals)
        
        # ANALYSIS 3: Optimized Search Query (leverage signals if no searches)
        analysis["recommended_search_query"] = _generate_optimized_query(clean_searches, analysis["search_clusters"], signal_insights)
        
        # ANALYSIS 4: Additional Insights (incorporate signal insights)
        analysis["intent_insights"] = _extract_intent_insights(clean_searches, signal_insights)
        
    except Exception as e:
        # Return safe defaults on error with signal fallback
        if past_signals:
            signal_insights = _extract_signal_insights(past_signals)
            analysis["recommended_search_query"] = _generate_query_from_signals(signal_insights)
        elif search_history:
            analysis["recommended_search_query"] = search_history[-1]
    
    return analysis

def _extract_signal_insights(past_signals: list) -> dict:
    """Extract structured insights from signal objects with topic data and evidence"""
    insights = {
        "topic_dimensions": {},
        "topic_values": [],
        "evidence_patterns": [],
        "dominant_focus": "",
        "confidence_indicators": []
    }
    
    if not past_signals:
        return insights
    
    try:
        for signal in past_signals:
            # Skip if signal is not a dictionary
            if not isinstance(signal, dict):
                continue
                
            # Extract topic dimension and value
            topic = signal.get("topic", {})
            if isinstance(topic, dict):
                dimension = topic.get("dimension")
                value = topic.get("value")
                
                if dimension and value:
                    if dimension not in insights["topic_dimensions"]:
                        insights["topic_dimensions"][dimension] = []
                    insights["topic_dimensions"][dimension].append(value)
                    insights["topic_values"].append(f"{dimension}: {value}")
            
            # Extract evidence context
            evidence = signal.get("evidence", "")
            if evidence:
                insights["evidence_patterns"].append(evidence)
                
                # Look for confidence indicators in evidence
                if "low-confidence" in evidence.lower():
                    insights["confidence_indicators"].append("low")
                elif "high-confidence" in evidence.lower():
                    insights["confidence_indicators"].append("high")
                else:
                    insights["confidence_indicators"].append("medium")
        
        # Find dominant focus from most frequent topic values
        all_values = []
        for values in insights["topic_dimensions"].values():
            all_values.extend(values)
        
        if all_values:
            value_counts = {}
            for value in all_values:
                value_counts[value] = value_counts.get(value, 0) + 1
            insights["dominant_focus"] = max(value_counts, key=value_counts.get)
        
    except Exception as e:
        pass  # Return empty insights on error
    
    return insights

def _extract_signal_focus(past_signals: list) -> list:
    """Extract recent focus areas from signals"""
    focus_areas = []
    
    for signal in past_signals:
        # Skip if signal is not a dictionary
        if not isinstance(signal, dict):
            continue
            
        topic = signal.get("topic", {})
        if isinstance(topic, dict):
            dimension = topic.get("dimension")
            value = topic.get("value")
            if dimension and value:
                focus_areas.append(f"{value}")
    
    # Return last 3 unique focus areas
    unique_focus = []
    for area in reversed(focus_areas):
        if area not in unique_focus:
            unique_focus.append(area)
        if len(unique_focus) >= 3:
            break
    
    return list(reversed(unique_focus))

def _generate_query_from_signals(signal_insights: dict) -> str:
    """Generate search query from signal insights when no search history exists"""
    if signal_insights["dominant_focus"]:
        return signal_insights["dominant_focus"]
    elif signal_insights["topic_values"]:
        # Use the first topic value
        first_topic = signal_insights["topic_values"][0]
        if ": " in first_topic:
            return first_topic.split(": ", 1)[1]
        return first_topic
    
    return ""

def _identify_search_clusters(searches: list, signal_insights: dict) -> list:
    """Group searches by semantic similarity and incorporate signal topic data"""
    clusters = []
    
    # Start with signal-based clusters
    topic_dimensions = signal_insights.get("topic_dimensions", {})
    for dimension, values in topic_dimensions.items():
        unique_values = list(set(values))
        if len(unique_values) == 1:
            clusters.append(f"{dimension}: {unique_values[0]}")
        elif len(unique_values) > 1:
            clusters.append(f"{dimension}: {', '.join(unique_values[:3])}")  # Top 3 values
    
    # Add search-based clustering if searches exist
    if searches:
        keyword_groups = {}
        
        for search in searches:
            words = search.split()
            
            # Look for product categories and attributes
            category_keywords = ['shoes', 'dress', 'shirt', 'pants', 'jacket', 'bag', 'watch', 'phone', 'laptop', 'bread', 'bakery']
            attribute_keywords = ['running', 'casual', 'formal', 'winter', 'summer', 'waterproof', 'wireless']
            
            found_categories = [word for word in words if any(cat in word for cat in category_keywords)]
            found_attributes = [word for word in words if any(attr in word for attr in attribute_keywords)]
            
            if found_categories:
                category = found_categories[0]
                if category not in keyword_groups:
                    keyword_groups[category] = []
                keyword_groups[category].extend(found_attributes)
        
        # Convert to clusters list
        for category, attributes in keyword_groups.items():
            unique_attrs = list(set(attributes))
            if unique_attrs:
                clusters.append(f"{category} with {', '.join(unique_attrs)}")
            else:
                clusters.append(category)
    
    return clusters[:3]  # Return top 3 clusters

def _generate_optimized_query(searches: list, clusters: list, signal_insights: dict) -> str:
    """Generate an optimized search query based on search patterns and signal insights"""
    # Priority 1: Use most recent search if available and specific enough
    if searches:
        latest_search = searches[-1]
        if len(latest_search.split()) >= 2:
            return latest_search
        # If latest search is too simple, enhance with signal data
        elif signal_insights.get("dominant_focus"):
            return f"{latest_search} {signal_insights['dominant_focus']}"
        elif clusters:
            return f"{latest_search} {clusters[0]}"
        else:
            return latest_search
    
    # Priority 2: Generate from signal insights when no searches
    signal_query = _generate_query_from_signals(signal_insights)
    if signal_query:
        return signal_query
    
    # Priority 3: Use clusters if available
    if clusters:
        return clusters[0]
    
    return ""

def _extract_intent_insights(searches: list, signal_insights: dict) -> dict:
    """Extract additional intent insights from searches and signal data"""
    insights = {
        "has_size_mentions": any(size in ' '.join(searches).lower() for size in ['small', 'medium', 'large', 'xl', 'size']) if searches else False,
        "dominant_topic_dimension": "",
        "behavioral_indicators": []
    }
    
    # Add signal-based insights
    topic_dimensions = signal_insights.get("topic_dimensions", {})
    if topic_dimensions:
        # Find most frequent dimension
        dimension_counts = {dim: len(values) for dim, values in topic_dimensions.items()}
        insights["dominant_topic_dimension"] = max(dimension_counts, key=dimension_counts.get)
    
    # Extract behavioral indicators from evidence
    evidence_patterns = signal_insights.get("evidence_patterns", [])
    for evidence in evidence_patterns:
        evidence_lower = evidence.lower()
        if "no add-to-cart" in evidence_lower:
            insights["behavioral_indicators"].append("browsing_without_purchasing")
        if "limited exploration" in evidence_lower:
            insights["behavioral_indicators"].append("focused_browsing")
        if "small number of products" in evidence_lower:
            insights["behavioral_indicators"].append("selective_viewing")
        if "know what kind of product" in evidence_lower:
            insights["behavioral_indicators"].append("intent_clarity")
    
    return insights
