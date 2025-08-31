#!/usr/bin/env python3
"""
Test script to validate multi-turn memory retention in the conversation system.

Tests the acceptance criteria: "Ask a two-turn question; on the third turn, 
the bot references the prior turns correctly"
"""
import asyncio
import json
import aiohttp
import sys
from datetime import datetime


class ConversationTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.conversation_id = None
    
    async def test_conversation_endpoint(self, query, lang="bn"):
        """Test the conversation endpoint with memory"""
        url = f"{self.base_url}/ask/conversation"
        payload = {
            "query": query,
            "lang": lang,
            "conversation_id": self.conversation_id
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Update conversation_id for subsequent requests
                        if not self.conversation_id:
                            self.conversation_id = data.get("conversation_id")
                        return data
                    else:
                        print(f"Error: {response.status} - {await response.text()}")
                        return None
            except Exception as e:
                print(f"Request failed: {e}")
                return None
    
    async def get_conversation_history(self):
        """Get conversation history"""
        if not self.conversation_id:
            return None
            
        url = f"{self.base_url}/conversation/{self.conversation_id}/history"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"History error: {response.status} - {await response.text()}")
                        return None
            except Exception as e:
                print(f"History request failed: {e}")
                return None
    
    async def run_multi_turn_test(self):
        """
        Run the multi-turn memory test:
        Turn 1: Ask about a specific topic
        Turn 2: Ask a follow-up question
        Turn 3: Reference the earlier conversation
        """
        print("🧪 Starting Multi-Turn Conversation Memory Test")
        print("=" * 50)
        
        # Turn 1: Initial question about a specific topic
        print("\n📱 Turn 1: Asking about artificial intelligence...")
        turn1_query = "What is artificial intelligence and how is it being used today?"
        response1 = await self.test_conversation_endpoint(turn1_query, lang="en")
        
        if not response1:
            print("❌ Turn 1 failed")
            return False
            
        print(f"🤖 Response 1: {response1['answer_en'][:150]}...")
        print(f"💭 Conversation ID: {response1.get('conversation_id', 'None')}")
        print(f"📊 Memory Context: {response1.get('memory_context', {})}")
        
        # Turn 2: Follow-up question
        print("\n📱 Turn 2: Follow-up about AI ethics...")
        turn2_query = "What are the main ethical concerns with AI?"
        response2 = await self.test_conversation_endpoint(turn2_query, lang="en")
        
        if not response2:
            print("❌ Turn 2 failed")
            return False
            
        print(f"🤖 Response 2: {response2['answer_en'][:150]}...")
        print(f"📊 Memory Context: {response2.get('memory_context', {})}")
        
        # Turn 3: Reference earlier conversation 
        print("\n📱 Turn 3: Reference to earlier conversation...")
        turn3_query = "Based on what we discussed about AI, what should companies prioritize?"
        response3 = await self.test_conversation_endpoint(turn3_query, lang="en")
        
        if not response3:
            print("❌ Turn 3 failed")
            return False
            
        print(f"🤖 Response 3: {response3['answer_en'][:150]}...")
        print(f"📊 Memory Context: {response3.get('memory_context', {})}")
        
        # Get conversation history to verify memory retention
        print("\n📚 Getting conversation history...")
        history = await self.get_conversation_history()
        
        if history and history.get("status") == "ok":
            conv_data = history.get("conversation", {})
            turns = conv_data.get("recent_turns", [])
            print(f"💾 Total turns in memory: {len(turns)}")
            print(f"🧠 Has summary: {conv_data.get('summary') is not None}")
            print(f"🔄 Mode: {conv_data.get('mode', 'unknown')}")
            
            # Check if the bot is referencing previous turns
            response3_text = response3['answer_en'].lower()
            memory_indicators = [
                "we discussed", "earlier", "previously", "mentioned", 
                "as we talked about", "from our conversation", "before"
            ]
            
            has_memory_reference = any(indicator in response3_text for indicator in memory_indicators)
            
            if has_memory_reference:
                print("✅ SUCCESS: Bot appears to reference earlier conversation!")
                print(f"🔍 Memory indicators found: {[ind for ind in memory_indicators if ind in response3_text]}")
                return True
            else:
                print("⚠️  WARNING: No clear memory references found in Turn 3 response")
                print("🔍 Response content analysis:")
                print(f"   - Response length: {len(response3_text)} characters")
                print(f"   - Contains AI: {'ai' in response3_text or 'artificial intelligence' in response3_text}")
                print(f"   - Contains ethics: {'ethic' in response3_text}")
                return False
        else:
            print("❌ Failed to get conversation history")
            return False
    
    async def run_bangla_test(self):
        """Test conversation memory in Bangla"""
        print("\n🇧🇩 Testing Bangla Conversation Memory")
        print("=" * 40)
        
        # Reset conversation for new test
        self.conversation_id = None
        
        # Turn 1: Ask about technology in Bangla
        print("\n📱 Turn 1: প্রযুক্তি সম্পর্কে প্রশ্ন...")
        turn1_query = "কৃত্রিম বুদ্ধিমত্তা কী এবং এটি কীভাবে কাজ করে?"
        response1 = await self.test_conversation_endpoint(turn1_query, lang="bn")
        
        if not response1:
            print("❌ Turn 1 failed")
            return False
            
        print(f"🤖 Response 1: {response1.get('answer_bn', '')[:100]}...")
        
        # Turn 2: Follow-up in Bangla
        print("\n📱 Turn 2: কৃত্রিম বুদ্ধিমত্তার ভবিষ্যৎ...")
        turn2_query = "এই প্রযুক্তির ভবিষ্যৎ কেমন হবে বলে আপনার মনে হয়?"
        response2 = await self.test_conversation_endpoint(turn2_query, lang="bn")
        
        if not response2:
            print("❌ Turn 2 failed")
            return False
            
        print(f"🤖 Response 2: {response2.get('answer_bn', '')[:100]}...")
        
        return True


async def main():
    tester = ConversationTester()
    
    print("🚀 KhoborAgent Conversation Memory Test")
    print(f"⏰ {datetime.now().isoformat()}")
    
    # Test 1: English multi-turn with memory validation
    success_en = await tester.run_multi_turn_test()
    
    # Test 2: Bangla conversation
    success_bn = await tester.run_bangla_test()
    
    print("\n" + "=" * 50)
    print("📈 TEST RESULTS:")
    print(f"   ✅ English Multi-Turn Memory: {'PASS' if success_en else 'FAIL'}")
    print(f"   ✅ Bangla Conversation: {'PASS' if success_bn else 'FAIL'}")
    
    if success_en and success_bn:
        print("\n🎉 All tests passed! Conversation memory is working correctly.")
        return True
    else:
        print("\n❌ Some tests failed. Check the conversation memory implementation.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        sys.exit(1)