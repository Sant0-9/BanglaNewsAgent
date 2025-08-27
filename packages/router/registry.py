import importlib
from typing import Callable, Optional

# Handler registry mapping intents to their handler modules
HANDLERS = {
    "weather": "handlers.weather:handle",
    "markets": "handlers.markets:handle", 
    "sports": "handlers.sports:handle",
    "lookup": "handlers.lookup:handle",
    "news": "handlers.news:handle"   # existing news pipeline
}

def resolve_handler(intent: str) -> Optional[Callable]:
    """
    Resolve and import handler function for given intent
    
    Args:
        intent: Intent name (weather, markets, sports, lookup, news)
        
    Returns:
        Callable handler function or None if not found
    """
    if intent not in HANDLERS:
        return None
    
    handler_path = HANDLERS[intent]
    
    try:
        # Parse module:function format
        if ':' not in handler_path:
            raise ValueError(f"Invalid handler path format: {handler_path}")
            
        module_path, function_name = handler_path.split(':', 1)
        
        # Import module dynamically
        module = importlib.import_module(module_path)
        
        # Get the handler function
        handler_func = getattr(module, function_name)
        
        return handler_func
        
    except (ImportError, AttributeError, ValueError) as e:
        print(f"Failed to resolve handler for intent '{intent}': {e}")
        return None

def get_available_intents() -> list:
    """Return list of available intents"""
    return list(HANDLERS.keys())

def register_handler(intent: str, handler_path: str) -> bool:
    """
    Register a new intent handler
    
    Args:
        intent: Intent name
        handler_path: Module path in format "module.path:function_name"
        
    Returns:
        True if registration successful, False otherwise
    """
    try:
        # Validate format
        if ':' not in handler_path:
            raise ValueError("Handler path must be in format 'module:function'")
            
        # Test if handler can be resolved
        test_handler = resolve_handler_path(handler_path)
        if test_handler is None:
            return False
            
        # Register if valid
        HANDLERS[intent] = handler_path
        return True
        
    except Exception as e:
        print(f"Failed to register handler for intent '{intent}': {e}")
        return False

def resolve_handler_path(handler_path: str) -> Optional[Callable]:
    """Helper to resolve a handler path without registering"""
    try:
        module_path, function_name = handler_path.split(':', 1)
        module = importlib.import_module(module_path)
        return getattr(module, function_name)
    except Exception:
        return None

# Example usage and testing
if __name__ == "__main__":
    # Test handler resolution
    intents_to_test = ["weather", "markets", "news"]
    
    for intent in intents_to_test:
        print(f"Testing intent: {intent}")
        handler = resolve_handler(intent)
        if handler:
            print(f"  ✓ Handler resolved: {handler}")
        else:
            print(f"  ✗ Handler not found or failed to import")
        print()
    
    print("Available intents:", get_available_intents())