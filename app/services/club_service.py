"""공독의 장 — 독서 모임 서비스 (인메모리 Mock)"""
import uuid
from datetime import datetime
from typing import Optional

_clubs = [
    {"club_id":"club_001","name":"철학 독서 모임","description":"고전 철학부터 현대 철학까지.","host_user_id":"user_demo","member_ids":["user_demo","user_002","user_003","user_004","user_005","user_006"],"current_book_title":"사피엔스","current_book_author":"유발 하라리","is_private":False,"tags":["철학","역사","인문학"],"emoji":"📖","created_at":"2025-03-01T10:00:00","is_live":True},
    {"club_id":"club_002","name":"SF 탐험대","description":"상상력의 끝을 탐험하는 SF 소설 모임.","host_user_id":"user_007","member_ids":["user_demo","user_007","user_008","user_009"],"current_book_title":"1984","current_book_author":"조지 오웰","is_private":False,"tags":["SF","디스토피아"],"emoji":"🌌","created_at":"2025-03-10T14:00:00","is_live":False},
    {"club_id":"club_003","name":"가족 독서 클럽","description":"세대를 넘어 함께 읽는 모임.","host_user_id":"user_demo","member_ids":["user_demo","user_010","user_011"],"current_book_title":"어린왕자","current_book_author":"생텍쥐페리","is_private":True,"tags":["가족","감성","고전"],"emoji":"🌿","created_at":"2025-03-20T09:00:00","is_live":False},
]

_cards = [
    {"card_id":"card_001","club_id":"club_001","user_id":"user_002","user_name":"지민","user_emoji":"🦋","type":"quote","content":"\"역사상 가장 중요한 사실은, 일단 인류가 무언가를 집단적으로 상상하기 시작하면, 그것은 점점 더 강력한 힘을 갖게 된다는 것이다.\" — 유발 하라리","book_page":None,"likes":["user_demo","user_003","user_004"],"comments":[],"created_at":"2025-04-01T09:15:00","is_ai":False},
    {"card_id":"card_002","club_id":"club_001","user_id":"user_003","user_name":"현우","user_emoji":"🌊","type":"thought","content":"화폐도 국가도 법도 결국 모두 '허구'인데, 이 허구들이 없다면 우리가 살아가는 세계 자체가 붕괴되겠죠. 허구가 현실보다 더 강력한 힘을 가진다는 게 오히려 인간의 위대함 아닐까요?","book_page":None,"likes":["user_demo","user_002"],"comments":[{"user_name":"지민","user_emoji":"🦋","content":"맞아요! 허구를 만드는 능력이 인류의 초능력인 것 같아요","created_at":"2025-04-01T09:30:00"}],"created_at":"2025-04-01T09:20:00","is_ai":False},
    {"card_id":"card_003","club_id":"club_001","user_id":"ai_luma","user_name":"LUMA AI","user_emoji":"✦","type":"ai_question","content":"만약 인류가 '허구를 믿는 능력'을 잃는다면, 지금 우리 사회에서 가장 먼저 사라지는 것은 무엇일까요? 그리고 그게 과연 나쁜 일일까요?","book_page":None,"likes":["user_demo","user_002","user_003","user_004","user_005"],"comments":[{"user_name":"현우","user_emoji":"🌊","content":"화폐가 가장 먼저 사라지지 않을까요?","created_at":"2025-04-01T10:05:00"},{"user_name":"지민","user_emoji":"🦋","content":"종교도 사라지겠죠","created_at":"2025-04-01T10:10:00"}],"created_at":"2025-04-01T10:00:00","is_ai":True},
    {"card_id":"card_004","club_id":"club_001","user_id":"user_004","user_name":"수아","user_emoji":"🌸","type":"insight","content":"사피엔스를 읽다 보니 어린왕자의 한 구절이 떠올랐어요. '어른들은 숫자를 좋아한다.' 어른들이 만든 허구의 세계가 결국 숫자(화폐, 주가, GDP)로 가득 차 있다는 것, 어쩌면 생텍쥐페리도 이걸 비판하고 싶었던 게 아닐까요?","book_page":None,"likes":["user_demo","user_002","user_003"],"comments":[],"created_at":"2025-04-01T11:30:00","is_ai":False},
    {"card_id":"card_005","club_id":"club_002","user_id":"user_007","user_name":"태양","user_emoji":"☀️","type":"quote","content":"\"전쟁은 평화다. 자유는 예속이다. 무지는 힘이다.\" — 조지 오웰, 1984","book_page":17,"likes":["user_demo","user_008"],"comments":[],"created_at":"2025-04-02T14:00:00","is_ai":False},
    {"card_id":"card_006","club_id":"club_002","user_id":"ai_luma","user_name":"LUMA AI","user_emoji":"✦","type":"ai_question","content":"빅브라더의 감시 사회와 현재 소셜미디어 세계, 어느 쪽이 더 자유롭다고 생각하시나요?","book_page":None,"likes":["user_demo","user_007","user_008","user_009"],"comments":[],"created_at":"2025-04-02T15:00:00","is_ai":True},
    {"card_id":"card_007","club_id":"club_003","user_id":"user_010","user_name":"엄마","user_emoji":"🌷","type":"thought","content":"어린왕자를 20년 만에 다시 읽었는데, 아이였을 때와 완전히 다르게 읽혀요. 그때는 여우가 신기했는데, 지금은 장미가 더 마음에 걸려요.","book_page":None,"likes":["user_demo","user_011"],"comments":[{"user_name":"나","user_emoji":"⭐","content":"저도요! 장미 입장에서 읽으니 더 슬프더라고요","created_at":"2025-04-02T20:30:00"}],"created_at":"2025-04-02T20:00:00","is_ai":False},
]

_reports = []

def get_all_clubs(user_id="user_demo"):
    result = []
    for c in _clubs:
        club = {**c}
        club["id"] = c["club_id"]
        club["current_book"] = c.get("current_book_title", "")
        club["current_book_author"] = c.get("current_book_author", "")
        club["member_count"] = len(c.get("member_ids",[]))
        club["is_member"]    = user_id in c.get("member_ids",[])
        club["card_count"]   = len([x for x in _cards if x["club_id"]==c["club_id"]])
        result.append(club)
    return result

def get_club(club_id, user_id="user_demo"):
    c = next((x for x in _clubs if x["club_id"]==club_id), None)
    if not c: return None
    return {
        **c,
        "id": c["club_id"],
        "current_book": c.get("current_book_title", ""),
        "current_book_author": c.get("current_book_author", ""),
        "member_count":len(c.get("member_ids",[])),
        "is_member":user_id in c.get("member_ids",[]),
        "card_count":len([x for x in _cards if x["club_id"]==club_id]),
    }

def create_club(data):
    club = {"club_id":f"club_{uuid.uuid4().hex[:6]}","name":data.get("name","새 모임"),"description":data.get("description",""),"host_user_id":data.get("user_id","user_demo"),"member_ids":[data.get("user_id","user_demo")],"current_book_title":data.get("book_title",""),"current_book_author":data.get("book_author",""),"is_private":data.get("is_private",False),"tags":data.get("tags",[]),"emoji":data.get("emoji","📚"),"created_at":datetime.now().isoformat(),"is_live":False}
    _clubs.insert(0, club)
    return {**club, "id": club["club_id"], "current_book": club.get("current_book_title", "")}

def join_club(club_id, user_id):
    c = next((x for x in _clubs if x["club_id"]==club_id), None)
    if not c: return {"ok":False,"error":"모임 없음"}
    if user_id not in c["member_ids"]: c["member_ids"].append(user_id)
    return {"ok":True,"member_count":len(c["member_ids"])}

def get_cards(club_id, limit=30):
    cards = sorted([c for c in _cards if c["club_id"]==club_id], key=lambda x: x["created_at"], reverse=True)
    return [{**c,"id":c["card_id"],"author_name":c.get("user_name",""),"like_count":len(c.get("likes",[])),"comment_count":len(c.get("comments",[])),"is_liked":"user_demo" in c.get("likes",[])} for c in cards[:limit]]

def create_card(club_id, data):
    card = {"card_id":f"card_{uuid.uuid4().hex[:8]}","club_id":club_id,"user_id":data.get("user_id","user_demo"),"user_name":data.get("user_name","나"),"user_emoji":data.get("user_emoji","⭐"),"type":data.get("type","thought"),"content":data.get("content",""),"book_page":data.get("book_page"),"likes":[],"comments":[],"created_at":datetime.now().isoformat(),"is_ai":False}
    _cards.insert(0, card)
    return {**card,"id":card["card_id"],"author_name":card.get("user_name","나"),"like_count":0,"comment_count":0,"is_liked":False}

def toggle_like(card_id, user_id="user_demo"):
    c = next((x for x in _cards if x["card_id"]==card_id), None)
    if not c: return {"ok":False,"error":"카드 없음"}
    likes = c.setdefault("likes",[])
    if user_id in likes: likes.remove(user_id); liked=False
    else: likes.append(user_id); liked=True
    return {"ok":True,"liked":liked,"like_count":len(likes)}

def add_comment(card_id, data):
    c = next((x for x in _cards if x["card_id"]==card_id), None)
    if not c: return {"ok":False,"error":"카드 없음"}
    cm = {"user_name":data.get("user_name","나"),"user_emoji":data.get("user_emoji","⭐"),"content":data.get("content",""),"created_at":datetime.now().isoformat()}
    c.setdefault("comments",[]).append(cm)
    return {"ok":True,"comment":cm,"comment_count":len(c["comments"])}

def update_club_settings(club_id, data):
    c = next((x for x in _clubs if x["club_id"]==club_id), None)
    if not c:
        return {"ok":False,"error":"모임을 찾을 수 없습니다."}
    if "current_book" in data or "current_book_title" in data:
        c["current_book_title"] = data.get("current_book") or data.get("current_book_title") or ""
    if "current_book_author" in data:
        c["current_book_author"] = data.get("current_book_author") or ""
    if "name" in data and str(data.get("name") or "").strip():
        c["name"] = str(data["name"]).strip()
    if "description" in data:
        c["description"] = data.get("description") or ""
    return {"ok":True,"club":get_club(club_id)}

def delete_club(club_id, user_id="user_demo"):
    global _clubs, _cards
    c = next((x for x in _clubs if x["club_id"]==club_id), None)
    if not c:
        return {"ok":False,"error":"모임방을 찾을 수 없습니다."}
    if c.get("host_user_id") not in {user_id, "user_demo"} and user_id != "user_demo":
        return {"ok":False,"error":"모임장만 삭제할 수 있습니다."}
    _clubs = [x for x in _clubs if x["club_id"]!=club_id]
    _cards = [x for x in _cards if x.get("club_id")!=club_id]
    return {"ok":True,"deleted_id":club_id}

def add_ai_card(club_id, question):
    card = {"card_id":f"card_ai_{uuid.uuid4().hex[:6]}","club_id":club_id,"user_id":"ai_luma","user_name":"LUMA AI","user_emoji":"✦","type":"ai_question","content":question,"book_page":None,"likes":[],"comments":[],"created_at":datetime.now().isoformat(),"is_ai":True,"like_count":0,"comment_count":0,"is_liked":False}
    _cards.insert(0, card)
    return card

def save_report(club_id, report):
    doc = {"report_id":f"report_{uuid.uuid4().hex[:6]}","club_id":club_id,"created_at":datetime.now().isoformat(),**report}
    _reports.insert(0, doc)
    return doc

def get_latest_report(club_id):
    return next((r for r in _reports if r["club_id"]==club_id), None)
