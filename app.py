import os
from flask import Flask, request, jsonify
from slack_sdk import WebClient

app = Flask(__name__)

# CONNECT SCRIPT TO SLACK SANDBOX TOKENS
SLACK_BOT_TOKEN = ""YOUR_BOT_XOXB_TOKEN_HERE""
SLACK_USER_TOKEN = "YOUR_USER_XOXP_TOKEN_HERE"

ADMIN_SLACK_ID = "YOUR_COPIED_MEMBER_ID_HERE"

bot_client = WebClient(token=SLACK_BOT_TOKEN)
user_client = WebClient(token=SLACK_USER_TOKEN)

question_database = {}

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    
    if data and "challenge" in data:
        return jsonify({"challenge": data["challenge"]})
        
    if data and "event" in data:
        event = data["event"]
        
        if event.get("type") == "message" and not event.get("bot_id"):
            message_text = event.get("text", "").strip()
            channel_id = event.get("channel")
            user_id = event.get("user")
            
            if message_text.endswith("?"):
                question_database[user_id] = question_database.get(user_id, 0) + 1
                current_count = question_database[user_id]
                
                sorted_database = sorted(question_database.items(), key=lambda item: item[1], reverse=True)
                print("\n📊 --- REAL-TIME DATA ENGINE: LOGGING TRACKER ---")
                print("MEMBERS          | QUESTIONS")
                print("----------------------------")
                for member, count in sorted_database:
                    print(f"<@{member}>     | {count}")
                print("---------------------------------------------------\n")
                
                if current_count >= 3:
                    print(f"🚨 CRITICAL ALARM: User <@{user_id}> hit the struggling learner threshold!")
                    
                    bot_client.chat_postMessage(
                        channel=ADMIN_SLACK_ID, 
                        text=f"⏳ *Proactive Learning Pipeline Triggered:* <@{user_id}> has logged *{current_count} questions* ending in '?'. Compiling workspace context via Real-Time Search API..."
                    )
                    
                    try:
                        rts_query = f"from:<@{user_id}>"
                        rts_response = user_client.search_messages(query=rts_query, count=5)
                        
                        context_summary = ""
                        if rts_response.get("ok"):
                            matches = rts_response.get("messages", {}).get("matches", [])
                            for idx, msg in enumerate(matches, 1):
                                text = msg.get("text", "")
                                context_summary += f"   {idx}. \"_{text}_\"\n"
                        
                        if not context_summary:
                            context_summary = "   _No prior searchable query history available._\n"
                            
                        alert_payload = (
                            f"🚨 *AI LEARNING COORDINATOR ALERT* 🚨\n\n"
                            f"👤 *Struggling Learner Identified:* <@{user_id}>\n"
                            f"📈 *Total Query Volume:* {current_count} questions tracked\n"
                            f"📡 *Real-Time Search (RTS) Historical Query Logs:*\n{context_summary}\n"
                            f"🎯 *Next System Actions:* Auto-initializing Study Group creation routines & mentor availability mapping dashboards..."
                        )
                        
                        bot_client.chat_postMessage(channel=ADMIN_SLACK_ID, text=alert_payload)
                        
                    except Exception as e:
                        print(f"RTS Execution Failure: {e}")
                        
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)