[
  {
    "$source": {
      "coll": "session_state",
      "config": {
        "fullDocument": "updateLookup"
      },
      "connectionName": "retail_customer_retention",
      "db": "leafy_popup_store",
      "timeField": {
        "$toDate": "$fullDocument.last10s.window.end"
      }
    }
  },
  {
    "$replaceRoot": {
      "newRoot": "$fullDocument"
    }
  },
  {
    "$match": {
      "last10s.intent.articleTypes": {
        "$type": "array"
      },
      "last10s.intent.products": {
        "$type": "array"
      },
      "last10s.intent.subCategories": {
        "$type": "array"
      },
      "last10s.window.end": {
        "$exists": true
      },
      "sessionId": {
        "$type": "string"
      },
      "userId": {
        "$type": "string"
      }
    }
  },
  {
    "$tumblingWindow": {
      "allowedLateness": 0,
      "boundary": "eventTime",
      "idleTimeout": 0,
      "interval": {
        "size": 30,
        "unit": "second"
      },
      "pipeline": [
        {
          "$group": {
            "_id": "$sessionId",
            "sid": {
              "$first": "$sessionId"
            },
            "snapshots": {
              "$push": {
                "articleTypes": "$last10s.intent.articleTypes",
                "end": "$last10s.window.end",
                "products": "$last10s.intent.products",
                "start": "$last10s.window.start",
                "subCategories": "$last10s.intent.subCategories"
              }
            },
            "uid": {
              "$first": "$userId"
            }
          }
        },
        {
          "$project": {
            "_id": 0,
            "signals": {
              "$function": {
                "args": [
                  "$sid",
                  "$uid",
                  "$snapshots"
                ],
                "body": "function(sid, uid, snapshots){\n  if(!Array.isArray(snapshots) || snapshots.length === 0) return [];\n\n  snapshots = snapshots.slice().sort((a,b)=>{\n    const ta = a && a.end ? new Date(a.end).getTime() : 0;\n    const tb = b && b.end ? new Date(b.end).getTime() : 0;\n    return ta - tb;\n  });\n\n  const fallbackTs = snapshots[snapshots.length-1] && snapshots[snapshots.length-1].end\n    ? new Date(snapshots[snapshots.length-1].end)\n    : new Date();\n\n  // Exclusion: any add-to-cart in the 30s window => no search-friction\n  let addToCartTotal = 0;\n  for (const snap of snapshots){\n    const prods = Array.isArray(snap.products) ? snap.products : [];\n    for (const p of prods){\n      if (p && typeof p.addToCartCount === 'number' && p.addToCartCount > 0) addToCartTotal += p.addToCartCount;\n    }\n  }\n  if (addToCartTotal > 0) return [];\n\n  // Distinct products explored (views/searches already summarized into presence in products array)\n  const productSet = new Set();\n  let maxProductFocus = 0;\n\n  for (const snap of snapshots){\n    const prods = Array.isArray(snap.products) ? snap.products : [];\n    for (const p of prods){\n      const pid = p && p.productId != null ? String(p.productId) : null;\n      if (pid) productSet.add(pid);\n      if (p && typeof p.focus === 'number' && p.focus > maxProductFocus) maxProductFocus = p.focus;\n    }\n  }\n\n  const distinctProducts = productSet.size;\n\n  function pickDominant(list, valueField){\n    // Returns { value, topFocus, secondFocus }\n    const bestByValue = Object.create(null);\n\n    for (const snap of snapshots){\n      const arr = Array.isArray(snap[list]) ? snap[list] : [];\n      for (const it of arr){\n        const v = it && it[valueField] != null ? String(it[valueField]) : null;\n        if (!v) continue;\n        const f = (it && typeof it.focus === 'number') ? it.focus : 0;\n        if (!bestByValue[v] || f > bestByValue[v]) bestByValue[v] = f;\n      }\n    }\n\n    let topValue = null;\n    let topFocus = 0;\n    let secondFocus = 0;\n\n    for (const v of Object.keys(bestByValue)){\n      const f = bestByValue[v];\n      if (f > topFocus){\n        secondFocus = topFocus;\n        topFocus = f;\n        topValue = v;\n      } else if (f > secondFocus){\n        secondFocus = f;\n      }\n    }\n\n    return { value: topValue, topFocus, secondFocus };\n  }\n\n  const domAT = pickDominant('articleTypes', 'articleType');\n  const domSC = pickDominant('subCategories', 'subCategory');\n\n  // Helper: dominant means topFocus passes threshold and is strictly higher than second\n  function isDominant(dom, threshold){\n    if (!dom || !dom.value) return false;\n    if (!(typeof dom.topFocus === 'number')) return false;\n    if (dom.topFocus <= threshold) return false;\n    if (dom.topFocus <= dom.secondFocus) return false;\n    return true;\n  }\n\n  const out = [];\n\n  // SF-1: 2–4 distinct products + dominant focus > 0.5 at articleType/subCategory\n  if (distinctProducts >= 2 && distinctProducts <= 4){\n    const atDom = isDominant(domAT, 0.5);\n    const scDom = isDominant(domSC, 0.5);\n\n    if (!atDom && !scDom) return [];\n\n    if (atDom){\n      out.push({\n        uid: String(uid),\n        sid: String(sid),\n        signal: 'search-friction',\n        severity: 'low',\n        topic: { dimension: 'articleType', value: domAT.value },\n        evidence: \"Explored a small number of products in the last 30 seconds, while articleType focus remained predominant on '\" + domAT.value + \"'. No add-to-cart was detected, suggesting the user may know what kind of product they want, but the limited exploration makes this a low-confidence hypothesis\",\n        _tsFallback: fallbackTs\n      });\n    }\n\n    if (scDom){\n      out.push({\n        uid: String(uid),\n        sid: String(sid),\n        signal: 'search-friction',\n        severity: 'low',\n        topic: { dimension: 'subCategory', value: domSC.value },\n        evidence: \"Explored a small number of products in the last 30 seconds, while subCategory focus remained predominant on '\" + domSC.value + \"'. No add-to-cart was detected, suggesting the user may know what kind of product they want, but the limited exploration makes this a low-confidence hypothesis\",\n        _tsFallback: fallbackTs\n      });\n    }\n\n    return out;\n  }\n\n  // SF-2 / SF-3 require >4 products\n  if (distinctProducts > 4){\n    const atDomMed = isDominant(domAT, 0.3);\n    const scDomMed = isDominant(domSC, 0.3);\n\n    // SF-3: >5 products + no dominant focus at product/articleType/subCategory\n    // (\"No dominant focus\" interpreted exactly as: product not dominant (focus<=0.5) AND no dominant AT/SC even at 0.3)\n    const noProductDominance = !(maxProductFocus > 0.5);\n    const noTopicDominance = (!atDomMed && !scDomMed);\n\n    if (distinctProducts > 5 && noProductDominance && noTopicDominance){\n      out.push({\n        uid: String(uid),\n        sid: String(sid),\n        signal: 'search-friction',\n        severity: 'high',\n        evidence: 'The user explored many products in the last 30 seconds with scattered attention, no clear convergence on any subCategory or articleType, and no add-to-cart detected, suggesting a lack of direction or confidence to progress',\n        _tsFallback: fallbackTs\n      });\n      return out;\n    }\n\n    // SF-2: >4 products + dominant focus >0.3 at articleType/subCategory\n    if (!atDomMed && !scDomMed) return [];\n\n    if (atDomMed){\n      out.push({\n        uid: String(uid),\n        sid: String(sid),\n        signal: 'search-friction',\n        severity: 'medium',\n        topic: { dimension: 'articleType', value: domAT.value },\n        evidence: \"Explored a considerable number of products in the last 30 seconds, while articleType focus remained predominant on '\" + domAT.value + \"'. The absence of add-to-cart suggests stable topic-level intent combined with choice overload at the product level\",\n        _tsFallback: fallbackTs\n      });\n    }\n\n    if (scDomMed){\n      out.push({\n        uid: String(uid),\n        sid: String(sid),\n        signal: 'search-friction',\n        severity: 'medium',\n        topic: { dimension: 'subCategory', value: domSC.value },\n        evidence: \"Explored a considerable number of products in the last 30 seconds, while subCategory focus remained predominant on '\" + domSC.value + \"'. The absence of add-to-cart suggests stable topic-level intent combined with choice overload at the product level\",\n        _tsFallback: fallbackTs\n      });\n    }\n\n    return out;\n  }\n\n  return [];\n}",
                "lang": "js"
              }
            }
          }
        },
        {
          "$unwind": "$signals"
        },
        {
          "$replaceRoot": {
            "newRoot": "$signals"
          }
        }
      ]
    }
  },
  {
    "$addFields": {
      "ts": {
        "$ifNull": [
          "$_stream_meta.window.end",
          "$_tsFallback"
        ]
      }
    }
  },
  {
    "$unset": [
      "_tsFallback",
      "_stream_meta",
      "_id"
    ]
  },
  {
    "$merge": {
      "into": {
        "coll": "session_signals",
        "connectionName": "retail_customer_retention",
        "db": "leafy_popup_store"
      },
      "on": "_id",
      "whenMatched": "keepExisting",
      "whenNotMatched": "insert"
    }
  }
]