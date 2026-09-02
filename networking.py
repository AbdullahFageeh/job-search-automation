#!/usr/bin/env python3
"""
Networking Pipeline Manager — Track and manage your professional network.
Organize contacts by tier, track interaction history, suggest next steps.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from tabulate import tabulate

BASE_DIR = Path(__file__).parent
CONTACTS_FILE = BASE_DIR / "logs" / "contacts.json"

# Contact tiers
TIERS = {
    "1": {"name": "Inner Circle", "desc": "Close mentors, former managers, close colleagues", "touch_freq": 30},
    "2": {"name": "Strong Network", "desc": "Good relationships, reached out before", "touch_freq": 60},
    "3": {"name": "Warm Connections", "desc": "Met once/twice, exchanged info", "touch_freq": 90},
    "4": {"name": "Cold Targets", "desc": "People you want to connect with", "touch_freq": 120},
}

INTERACTION_TYPES = [
    "coffee_chat", "linkedin_message", "email", "call", "meeting",
    "introduction", "referred_job", "sent_info", "followed_up", "connected"
]

def load_contacts() -> list:
    """Load contacts from file."""
    if CONTACTS_FILE.exists():
        with open(CONTACTS_FILE) as f:
            return json.load(f)
    return []

def save_contacts(contacts: list):
    """Save contacts to file."""
    with open(CONTACTS_FILE, "w") as f:
        json.dump(contacts, f, indent=2)

def add_contact(name: str, email: str, company: str, role: str = "",
                tier: str = "3", linkedin: str = "", notes: str = "") -> dict:
    """Add a new contact."""
    contacts = load_contacts()
    
    # Check for duplicates
    for c in contacts:
        if c.get("email") == email or c.get("name") == name:
            print(f"⚠️  Contact '{name}' already exists.")
            return c
    
    contact = {
        "id": len(contacts) + 1,
        "name": name,
        "email": email,
        "company": company,
        "role": role,
        "tier": tier,
        "linkedin": linkedin,
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "interactions": [],
        "last_contacted": None,
    }
    
    contacts.append(contact)
    save_contacts(contacts)
    print(f"✅ Added: {name} ({company})")
    return contact

def add_interaction(contact_email: str, interaction_type: str, notes: str = ""):
    """Log an interaction with a contact."""
    contacts = load_contacts()
    for c in contacts:
        if c.get("email") == contact_email or c.get("name") == contact_email:
            c["interactions"].append({
                "type": interaction_type,
                "notes": notes,
                "date": datetime.now().isoformat(),
            })
            c["last_contacted"] = datetime.now().isoformat()
            save_contacts(contacts)
            print(f"✅ Logged {interaction_type} with {c['name']}")
            return c
    print(f"❌ Contact not found: {contact_email}")
    return None

def get_due_contacts() -> list:
    """Find contacts due for re-engagement."""
    contacts = load_contacts()
    due = []
    today = datetime.now().date()
    
    for c in contacts:
        tier_info = TIERS.get(c.get("tier", "3"))
        freq = tier_info["touch_freq"]
        
        last = c.get("last_contacted")
        if last:
            last_date = datetime.fromisoformat(last).date()
            days_since = (today - last_date).days
        else:
            days_since = 999  # Never contacted
        
        if days_since >= freq:
            c["_days_since"] = days_since
            c["_tier_name"] = tier_info["name"]
            due.append(c)
    
    return sorted(due, key=lambda x: x["_days_since"], reverse=True)

def suggest_reachouts() -> list:
    """Suggest contacts to reach out to based on target companies/roles."""
    contacts = load_contacts()
    suggestions = []
    
    # Prioritize: untouch contacts in target companies, tier 3-4 contacts
    target_companies = ["GitLab", "Stripe", "Shopify", "Linear", "Notion", "Figma", "Vercel"]
    
    for c in contacts:
        score = 0
        reasons = []
        
        # Never contacted
        if not c.get("last_contacted"):
            score += 10
            reasons.append("never contacted")
        
        # Target company
        if c.get("company", "") in target_companies:
            score += 5
            reasons.append("target company")
        
        # Higher tier (lower number)
        tier = int(c.get("tier", "3"))
        score += (4 - tier)
        
        if score > 0:
            c["_priority_score"] = score
            c["_reasons"] = reasons
            suggestions.append(c)
    
    return sorted(suggestions, key=lambda x: x["_priority_score"], reverse=True)[:10]

def generate_reachout_message(contact: dict, purpose: str = "general") -> str:
    """Generate a personalized outreach message."""
    tier = contact.get("tier", "3")
    last_contacted = contact.get("last_contacted")
    
    if tier == "1" or tier == "2":
        # Warm message
        if last_contacted:
            return f"""Hi {contact['name']},

Hope you're doing well! It's been a while since we last connected. 

I'm currently exploring new opportunities in {purpose} and would love to get your perspective given your experience at {contact.get('company', 'your company')}.

Would you be open to a quick chat sometime?

Best,
Abdullah"""
        else:
            return f"""Hi {contact['name']},

Great connecting with you! I'm currently exploring opportunities in {purpose} and would value your perspective.

Would you be open to a quick chat sometime?

Best,
Abdullah"""
    else:
        # Cold/warm message
        return f"""Hi {contact['name']},

I came across your profile and noticed your work at {contact.get('company', 'your company')}. I'm currently exploring roles in {purpose} and would love to learn from your experience.

Would you be open to a brief 15-minute chat?

Best regards,
Abdullah Fageeh"""

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Networking Pipeline Manager")
    sub = parser.add_subparsers(dest="action")
    
    # Add contact
    p_add = sub.add_parser("add", help="Add a new contact")
    p_add.add_argument("--name", "-n", required=True)
    p_add.add_argument("--email", "-e", required=True)
    p_add.add_argument("--company", "-c", default="")
    p_add.add_argument("--role", "-r", default="")
    p_add.add_argument("--tier", "-t", default="3", choices=["1", "2", "3", "4"])
    p_add.add_argument("--linkedin", "-l", default="")
    p_add.add_argument("--notes", default="")
    
    # Log interaction
    p_interact = sub.add_parser("interact", help="Log an interaction")
    p_interact.add_argument("email", help="Contact email or name")
    p_interact.add_argument("type", choices=INTERACTION_TYPES)
    p_interact.add_argument("--notes", default="")
    
    # List due
    sub.add_parser("due", help="Show contacts due for re-engagement")
    
    # Suggest
    sub.add_parser("suggest", help="Suggest contacts to reach out to")
    
    # Generate message
    p_msg = sub.add_parser("message", help="Generate outreach message")
    p_msg.add_argument("email", help="Contact email")
    p_msg.add_argument("--purpose", default="operations roles", help="Purpose of outreach")
    
    # List all
    p_list = sub.add_parser("list", help="List all contacts")
    p_list.add_argument("--tier", "-t", choices=["1", "2", "3", "4"], help="Filter by tier")
    
    # Stats
    sub.add_parser("stats", help="Show networking stats")
    
    args = parser.parse_args()
    
    if args.action == "add":
        add_contact(args.name, args.email, args.company, args.role, args.tier, args.linkedin, args.notes)
    
    elif args.action == "interact":
        add_interaction(args.email, args.type, args.notes)
    
    elif args.action == "due":
        due = get_due_contacts()
        if not due:
            print("✅ No contacts due for re-engagement right now.")
            return
        print(f"\n📬 {len(due)} contacts due for re-engagement:\n")
        for c in due:
            print(f"  {c['tier']}. {c['name']} ({c.get('company', '?')})")
            print(f"     {c['_days_since']} days since last contact | {c['_tier_name']}")
            print()
    
    elif args.action == "suggest":
        suggestions = suggest_reachouts()
        if not suggestions:
            print("No suggestions yet. Add more contacts first.")
            return
        print(f"\n🎯 Top contacts to reach out to:\n")
        for c in suggestions[:10]:
            print(f"  ⭐{c['_priority_score']} {c['name']} ({c.get('company', '?')})")
            print(f"     Reasons: {', '.join(c['_reasons'])}")
        print()
    
    elif args.action == "message":
        contacts = load_contacts()
        contact = next((c for c in contacts if c.get("email") == args.email or c.get("name") == args.email), None)
        if contact:
            msg = generate_reachout_message(contact, args.purpose)
            print(f"\n📧 Draft message for {contact['name']}:\n")
            print(msg)
        else:
            print(f"❌ Contact not found: {args.email}")
    
    elif args.action == "list":
        contacts = load_contacts()
        if args.tier:
            contacts = [c for c in contacts if c.get("tier") == args.tier]
        
        if not contacts:
            print("No contacts yet.")
            return
        
        rows = []
        for c in contacts:
            tier_info = TIERS.get(c.get("tier", "3"))
            rows.append([
                c.get("name", "?"),
                c.get("company", "?"),
                c.get("role", "?"),
                tier_info["name"],
                c.get("last_contacted", "never")[:10] if c.get("last_contacted") else "never",
                len(c.get("interactions", [])),
            ])
        
        print("\n" + tabulate(rows, headers=["Name", "Company", "Role", "Tier", "Last Contact", "Interactions"], tablefmt="simple"))
    
    elif args.action == "stats":
        contacts = load_contacts()
        total = len(contacts)
        by_tier = {str(i): sum(1 for c in contacts if c.get("tier") == str(i)) for i in range(1, 5)}
        by_company = {}
        for c in contacts:
            comp = c.get("company", "Unknown")
            by_company[comp] = by_company.get(comp, 0) + 1
        
        print(f"\n📊 Networking Stats")
        print(f"   Total contacts: {total}")
        print(f"\n   By Tier:")
        for tier, count in by_tier.items():
            tier_info = TIERS.get(tier)
            print(f"     {tier_info['name']}: {count}")
        
        if by_company:
            print(f"\n   Top Companies:")
            for comp, count in sorted(by_company.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"     {comp}: {count}")
        print()
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()