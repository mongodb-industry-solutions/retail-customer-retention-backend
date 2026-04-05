[
  {
    "$source": {
      "coll": "session_state",
      "config": {
        "fullDocument": "updateLookup"
      },
      "connectionName": "retail_customer_retention",
      "db": "leafy_popup_store",
      "timeField": "$fullDocument.lastSeen"
    }
  },
  {
    "$replaceRoot": {
      "newRoot": "$fullDocument"
    }
  },
  {
    "$match": {
      "last10s.lastEvent.event": {
        "$type": "string"
      },
      "lastSeen": {
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
      "allowedLateness": {
        "size": 30,
        "unit": "second"
      },
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
                "end": "$lastSeen",
                "lastEvent": "$last10s.lastEvent.event"
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
            "signalDoc": {
              "$function": {
                "args": [
                  "$sid",
                  "$uid",
                  "$snapshots"
                ],
                "body": "function(sid, uid, snapshots){\n  if(!Array.isArray(snapshots) || snapshots.length===0) return null;\n\n  snapshots = snapshots.slice().sort((a,b)=>{\n    const ta = a && a.end ? new Date(a.end).getTime() : 0;\n    const tb = b && b.end ? new Date(b.end).getTime() : 0;\n    return ta - tb;\n  });\n\n  const fallbackTs = snapshots[snapshots.length-1] && snapshots[snapshots.length-1].end\n    ? new Date(snapshots[snapshots.length-1].end)\n    : new Date();\n\n  let hits = 0;\n  for (const s of snapshots){\n    if (s && s.lastEvent === 'exit-risk') hits += 1;\n  }\n\n  if (hits <= 0) return null;\n\n  let severity = 'low';\n  if (hits === 2) severity = 'medium';\n  if (hits >= 3) severity = 'high';\n\n  let evidence = 'Early exit signals detected in the last 30 seconds.';\n  if (hits === 2) evidence = 'Repeated exit signals detected in the last 30 seconds.';\n  if (hits >= 3) evidence = 'Strong exit intent detected in the last 30 seconds.';\n\n  return { sid, uid, signal: 'exit-risk', severity, evidence, _tsFallback: fallbackTs };\n}",
                "lang": "js"
              }
            },
            "uid": 1
          }
        },
        {
          "$match": {
            "signalDoc": {
              "$ne": null
            }
          }
        },
        {
          "$replaceRoot": {
            "newRoot": "$signalDoc"
          }
        }
      ]
    }
  },
  {
    "$addFields": {
      "ts": {
        "$ifNull": [
          "$_tsFallback",
          "$_tsFallback"
        ]
      }
    }
  },
  {
    "$unset": [
      "_tsFallback",
      "_stream_meta"
    ]
  },
  {
    "$unset": [
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