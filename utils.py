from functools import wraps

import collections

def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(func)
        async def command_func(update, context, *args, **kwargs):
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=action)
            return await func(update, context,  *args, **kwargs)
        return command_func
    
    return decorator

def makeNestedDict():
    return collections.defaultdict(makeNestedDict)
