#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.

from pyrogram import Client 
from bot import Bot
from config import *
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.database import *
from helper_func import *

def safe_edit(msg, *args, **kwargs):
    """Safely edit text without MESSAGE_NOT_MODIFIED crashes."""
    try:
        return msg.edit_text(*args, **kwargs)
    except MessageNotModified:
        pass
    except Exception:
        pass


@Bot.on_callback_query()
async def cb_handler(client: Bot, query: CallbackQuery):
    data = query.data

    if data == "help":
        await query.message.edit_text(
            text=HELP_TXT.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                 InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data='close')]
            ])
        )

    elif data == "about":
        await query.message.edit_text(
            text=ABOUT_TXT.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                 InlineKeyboardButton('ᴄʟᴏꜱᴇ', callback_data='close')]
            ])
        )

    elif data == "start":
        await query.message.edit_text(
            text=START_MSG.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ʜᴇʟᴘ", callback_data='help'),
                 InlineKeyboardButton("ᴀʙᴏᴜᴛ", callback_data='about')]
            ])
        )


# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport
#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.
#


    elif data == "premium":
        await query.message.delete()
        await client.send_photo(
            chat_id=query.message.chat.id,
            photo=QR_PIC,
            caption=(
                f"<blockquote><b>👋Hello {query.from_user.username}</b></blockquote>\n\n"
                f"<blockquote><b>🏷 Pricing:</b>\n\n"
                f"● <b>{PRICE1} : For 7 Days Prime Membership</b>\n"
                f"● <b>{PRICE2} : For 1 Month Prime Membership</b>\n"
                f"● <b>{PRICE3} : For 3 Months Prime Membership</b>\n"
                f"● <b>{PRICE4} : For 6 Months Prime Membership</b>\n"
                f"● <b>{PRICE5} : For 1 Year Prime Membership</b></blockquote>\n\n\n"
                f"<blockquote>"
                f"<b>💵 Payment Methods We Accept Now:</b>\n"
                f"┏╼╾╼╾╼╾╼╾━\n"
                f"♲ <b>Gift Card</b>\n"
                f"♲ <b>Crypto</b>\n"
                f"┗╼╾╼╾╼╾╼╾━"
                f"</blockquote>\n\n"
                f"<b>⚠️ Important Notice:</b>\n"
                f"<blockquote>"
                f"Please note that the @Spicylinebun Premium Subscription is non-refundable once purchased.\n"
                f"We recommend reviewing all details carefully before completing your payment."
                f"</blockquote>\n\n\n"

                f"<b>🤙 To Buy: @Goathunterr</b>"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Send Giftcard/And payment (ᴀᴅᴍɪɴ)", url=(SCREENSHOT_URL)
                        )
                    ],
                    [
                        InlineKeyboardButton("ʙᴀᴄᴋ", callback_data="back_to_verify"),
                        InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close"),
                    ],
                ]
            )
        )



    elif data == "back_to_verify":
        user_id = query.from_user.id
        verify_status = await db.get_verify_status(user_id)
        shortlink = verify_status.get('link')
        await query.message.delete()

        btn = [
            [InlineKeyboardButton("ᴏᴘᴇɴ ʟɪɴᴋ", url=shortlink),
             InlineKeyboardButton("ᴛᴜᴛᴏʀɪᴀʟ", url=TUT_VID)],
            [InlineKeyboardButton("ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ", callback_data="premium")]
        ]
        await client.send_message(
            chat_id=query.message.chat.id,
            text=(
                f"Your token has expired. Please refresh to continue..\n\n"
                f"<b>Token Timeout:</b> {get_exp_time(VERIFY_EXPIRE)}\n\n"
                "<b>What is token?</b>\n"
                f"Pass one ad to use bot for {get_exp_time(VERIFY_EXPIRE)}"
            ),
            reply_markup=InlineKeyboardMarkup(btn)
        )

    elif data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass

    elif data.startswith("rfs_ch_"):
        cid = int(data.split("_")[2])
        try:
            chat = await client.get_chat(cid)
            mode = await db.get_channel_mode(cid)
            status = "🟢 ᴏɴ" if mode == "on" else "🔴 ᴏғғ"
            new_mode = "ᴏғғ" if mode == "on" else "on"
            buttons = [
                [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
                [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")]
            ]
            await query.message.edit_text(
                f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            await query.answer("Failed to fetch channel info", show_alert=True)

    elif data.startswith("rfs_toggle_"):
        cid, action = data.split("_")[2:]
        cid = int(cid)
        mode = "on" if action == "on" else "off"

        await db.set_channel_mode(cid, mode)
        await query.answer(f"Force-Sub set to {'ON' if mode == 'on' else 'OFF'}")

        # Refresh the same channel's mode view
        chat = await client.get_chat(cid)
        status = "🟢 ON" if mode == "on" else "🔴 OFF"
        new_mode = "off" if mode == "on" else "on"
        buttons = [
            [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
            [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")]
        ]
        await query.message.edit_text(
            f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == "fsub_back":
        channels = await db.show_channels()
        buttons = []
        for cid in channels:
            try:
                chat = await client.get_chat(cid)
                mode = await db.get_channel_mode(cid)
                status = "🟢" if mode == "on" else "🔴"
                buttons.append([InlineKeyboardButton(f"{status} {chat.title}", callback_data=f"rfs_ch_{cid}")])
            except:
                continue

        await query.message.edit_text(
            "sᴇʟᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛᴏɢɢʟᴇ ɪᴛs ғᴏʀᴄᴇ-sᴜʙ ᴍᴏᴅᴇ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport
#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.
#
