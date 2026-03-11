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
        "$toDate": "$fullDocument.last10s.window.start"
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
      "last10s.intent.products": {
        "$type": "array"
      },
      "last10s.window.end": {
        "$exists": true
      },
      "last10s.window.start": {
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
                "end": "$last10s.window.end",
                "products": "$last10s.intent.products",
                "start": "$last10s.window.start"
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
            "sid": 1,
            "signals": {
              "$function": {
                "args": [
                  "$sid",
                  "$uid",
                  "$snapshots"
                ],
                "body": "function(sid, uid, snapshots){\n  if(!Array.isArray(snapshots) || snapshots.length===0) return [];\n\n  snapshots = snapshots.slice().sort((a,b)=>{\n    const ta = a && a.start ? new Date(a.start).getTime() : 0;\n    const tb = b && b.start ? new Date(b.start).getTime() : 0;\n    return ta - tb;\n  });\n\n  const fallbackTs = snapshots[snapshots.length-1] && snapshots[snapshots.length-1].end\n    ? new Date(snapshots[snapshots.length-1].end)\n    : new Date();\n\n  const byProduct = Object.create(null);\n\n  for (const snap of snapshots){\n    const prods = Array.isArray(snap.products) ? snap.products : [];\n    for (const p of prods){\n      const pid = p && p.productId != null ? String(p.productId) : null;\n      if(!pid) continue;\n\n      if(!byProduct[pid]) byProduct[pid] = { focusHits: 0, addToCartTotal: 0 };\n\n      if (typeof p.focus === 'number' && p.focus >= 0.5) byProduct[pid].focusHits += 1;\n      if (typeof p.addToCartCount === 'number') byProduct[pid].addToCartTotal += p.addToCartCount;\n    }\n  }\n\n  const out = [];\n\n  for (const pid of Object.keys(byProduct)){\n    const st = byProduct[pid];\n\n    if (st.addToCartTotal > 0){\n      out.push({ sid, uid, signal: 'high-intent', severity: 'high', evidence: 'add-to-cart occurred for product in last 30s', productId: pid, _tsFallback: fallbackTs });\n      continue;\n    }\n\n    if (st.focusHits >= 3){\n      out.push({ sid, uid, signal: 'high-intent', severity: 'medium', evidence: 'product focus above 0.5 sustained in all 3 windows', productId: pid, _tsFallback: fallbackTs });\n      continue;\n    }\n\n    if (st.focusHits === 2){\n      out.push({ sid, uid, signal: 'high-intent', severity: 'low', evidence: 'product focus above 0.5 observed in 2 of last 3 windows', productId: pid, _tsFallback: fallbackTs });\n      continue;\n    }\n  }\n\n  return out;\n}",
                "lang": "js"
              }
            },
            "uid": 1
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