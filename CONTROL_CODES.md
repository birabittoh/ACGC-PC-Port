# Animal Crossing (USA) Message Control Codes

This document provides a detailed technical reference for the message control codes used in the USA version of Animal Crossing.

## Overview

Message data in Animal Crossing contains special sequences that control the display, logic, and dynamic content of dialogue.

- **Control Code Prefix**: `0x7F` (CHAR_CONTROL_CODE)
- **Format**: `0x7F [Type] [Parameters...]`
- **Parameter Encoding**: Parameters are typically single bytes (`u8`) or big-endian 16-bit integers (`u16`).

---

## Control Code Table

| Hex | Enum Name | Size | Parameters | Description |
| :--- | :--- | :--- | :--- | :--- |
| `0x00` | `LAST` | 2 | None | Terminates the current message string immediately. |
| `0x01` | `CONTINUE` | 2 | None | Pauses and waits for the player to press A or B before clearing the window and continuing. |
| `0x02` | `CLEAR` | 2 | None | Clears all text currently in the message window and resets the cursor to the top. |
| `0x03` | `CURSOR_SET_TIME` | 3 | `u8 delay` | Sets the time delay between individual characters being typed. `delay * 2` frames (at 60fps). |
| `0x04` | `BUTTON` | 2 | None | Pauses and waits for player input (A/B) to continue. |
| `0x05` | `COLOR` | 5 | `u8 r, g, b` | Sets the text color for the following text until the end of the line or next color change. |
| `0x06` | `ABLE_CANCEL` | 2 | None | Enables the player's ability to fast-forward or skip the current message. |
| `0x07` | `UNABLE_CANCEL` | 2 | None | Disables the player's ability to fast-forward or skip the current message. |
| `0x08` | `SET_DEMO_ORDER_PLAYER` | 5 | `u8 idx, u16 val` | Sets a value in the player character's demo order table. |
| `0x09` | `SET_DEMO_ORDER_NPC0` | 5 | `u8 idx, u16 val` | Sets a value in NPC 0's demo order table. |
| `0x0A` | `SET_DEMO_ORDER_NPC1` | 5 | `u8 idx, u16 val` | Sets a value in NPC 1's demo order table. |
| `0x0B` | `SET_DEMO_ORDER_NPC2` | 5 | `u8 idx, u16 val` | Sets a value in NPC 2's demo order table. |
| `0x0C` | `SET_DEMO_ORDER_QUEST` | 5 | `u8 idx, u16 val` | Sets a value in the current quest's demo order table. |
| `0x0D` | `SET_SELECT_WINDOW` | 2 | None | Triggers the appearance of the choice selection window. |
| `0x0E` | `SET_NEXT_MESSAGE_F` | 4 | `u16 msg_no` | Sets the ID of the next message to be loaded after this one finishes. |
| `0x0F` | `SET_NEXT_MESSAGE_0` | 4 | `u16 msg_no` | Sets the next message ID if choice 0 is picked in a selection window. |
| `0x10` | `SET_NEXT_MESSAGE_1` | 4 | `u16 msg_no` | Sets the next message ID if choice 1 is picked. |
| `0x11` | `SET_NEXT_MESSAGE_2` | 4 | `u16 msg_no` | Sets the next message ID if choice 2 is picked. |
| `0x12` | `SET_NEXT_MESSAGE_3` | 4 | `u16 msg_no` | Sets the next message ID if choice 3 is picked. |
| `0x13` | `SET_NEXT_MESSAGE_RANDOM_2` | 6 | `u16 m1, m2` | Randomly selects the next message ID from the 2 provided options. |
| `0x14` | `SET_NEXT_MESSAGE_RANDOM_3` | 8 | `u16 m1..m3` | Randomly selects the next message ID from the 3 provided options. |
| `0x15` | `SET_NEXT_MESSAGE_RANDOM_4` | 10 | `u16 m1..m4` | Randomly selects the next message ID from the 4 provided options. |
| `0x16` | `SET_SELECT_STRING_2` | 6 | `u16 s1, s2` | Sets the strings for 2 choices in the selection window. |
| `0x17` | `SET_SELECT_STRING_3` | 8 | `u16 s1..s3` | Sets the strings for 3 choices. |
| `0x18` | `SET_SELECT_STRING_4` | 10 | `u16 s1..s4` | Sets the strings for 4 choices. |
| `0x19` | `SET_FORCE_NEXT` | 2 | None | Forces the game to automatically load the next message ID without player input. |
| `0x1A` | `PUT_STRING_PLAYER_NAME` | 2 | None | Inserts the current player's name. |
| `0x1B` | `PUT_STRING_TALK_NAME` | 2 | None | Inserts the name of the NPC being spoken to. |
| `0x1C` | `PUT_STRING_TAIL` | 2 | None | Inserts the catchphrase of the NPC being spoken to. |
| `0x1D` | `PUT_STRING_YEAR` | 2 | None | Inserts the current year. |
| `0x1E` | `PUT_STRING_MONTH` | 2 | None | Inserts the current month (localized name). |
| `0x1F` | `PUT_STRING_WEEK` | 2 | None | Inserts the current day of the week (localized name). |
| `0x20` | `PUT_STRING_DAY` | 2 | None | Inserts the current day of the month. |
| `0x21` | `PUT_STRING_HOUR` | 2 | None | Inserts the current hour. |
| `0x22` | `PUT_STRING_MIN` | 2 | None | Inserts the current minute. |
| `0x23` | `PUT_STRING_SEC` | 2 | None | Inserts the current second. |
| `0x24-0x2D`| `PUT_STRING_FREE0-9` | 2 | None | Inserts a "free" dynamic string (0-9). Used for varied event-specific data. |
| `0x2E` | `PUT_STRING_DETERMINATION` | 2 | None | Inserts the string content of the choice last selected by the player. |
| `0x2F` | `PUT_STRING_COUNTRY_NAME` | 2 | None | Inserts the town name. |
| `0x30` | `PUT_STRING_RANDOM_NUMBER_2` | 2 | None | Inserts a random 2-digit number (00-99). |
| `0x31-0x35`| `PUT_STRING_ITEM0-4` | 2 | None | Inserts the name of a specific item (0-4). |
| `0x36-0x3F`| `PUT_STRING_FREE10-19` | 2 | None | Inserts a "free" dynamic string (10-19). |
| `0x40` | `PUT_STRING_MAIL` | 2 | None | Inserts the content of a mail message. |
| `0x41-0x4A`| `SET_PLAYER_DESTINY0-9` | 2 | None | Sets the player's luck/destiny state (e.g., money luck, friendship luck). |
| `0x4B` | `MESSAGE_CONTENTS_NORMAL` | 2 | None | Resets the NPC voice synthesis to the normal tone. |
| `0x4C` | `MESSAGE_CONTENTS_ANGRY` | 2 | None | Sets the NPC voice synthesis to an angry tone. |
| `0x4D` | `MESSAGE_CONTENTS_SAD` | 2 | None | Sets the NPC voice synthesis to a sad tone. |
| `0x4E` | `MESSAGE_CONTENTS_FUN` | 2 | None | Sets the NPC voice synthesis to a happy/excited tone. |
| `0x4F` | `MESSAGE_CONTENTS_SLEEPY` | 2 | None | Sets the NPC voice synthesis to a sleepy tone. |
| `0x50` | `SET_COLOR_CHAR` | 6 | `u8 r, g, b, count` | Sets text color for the next `count` characters only. |
| `0x51` | `SOUND_CUT` | 3 | `u8 flag` | If `flag` is 1, disables the "typing" sound effect for each character. |
| `0x52` | `SET_LINE_OFFSET` | 3 | `u8 offset` | Shifts the current line vertically by `offset - 128` pixels. |
| `0x53` | `SET_LINE_TYPE` | 3 | `u8 type` | Sets vertical alignment for the line: 0=Top, 1=Center, 2=Bottom. |
| `0x54` | `SET_CHAR_SCALE` | 3 | `u8 scale` | Sets the scale of the following characters (units of 1/32). |
| `0x55` | `BUTTON2` | 2 | None | Like `BUTTON`, but suppresses the page-turn sound effect. |
| `0x56` | `BGM_MAKE` | 4 | `u8 track, u8 stop` | Starts a specific BGM track. `stop` defines the transition type. |
| `0x57` | `BGM_DELETE` | 4 | `u8 track, u8 stop` | Stops a specific BGM track. |
| `0x58` | `MSG_TIME_END` | 3 | `u8 time` | Automatically closes the message after `time` has elapsed. |
| `0x59` | `SOUND_TRG_SYS` | 3 | `u8 se_no` | Plays a system sound effect. |
| `0x5A` | `SET_LINE_SCALE` | 3 | `u8 scale` | Sets the scale for the entire line (units of 1/32). |
| `0x5B` | `SOUND_NO_PAGE` | 2 | None | Disables the sound effect when advancing to the next message page. |
| `0x5C` | `VOICE_TRUE` | 2 | None | Enables animal voice synthesis. |
| `0x5D` | `VOICE_FALSE` | 2 | None | Disables animal voice synthesis. |
| `0x5E` | `SELECT_NO_B` | 2 | None | Disables the B button's ability to cancel/close the selection window. |
| `0x5F` | `GIVE_OPEN` | 2 | None | Logic gate: proceeds if an item hand-over is ready. |
| `0x60` | `GIVE_CLOSE` | 2 | None | Logic gate: proceeds if an item hand-over is not active. |
| `0x61` | `MESSAGE_CONTENTS_GLOOMY` | 2 | None | Sets the NPC voice synthesis to a gloomy tone. |
| `0x62` | `SELECT_NO_B_CLOSE` | 2 | None | Variant of `SELECT_NO_B` with different closing behavior. |
| `0x63` | `SET_NEXT_MESSAGE_RANDOM_SECTION` | 6 | `u16 base, u16 max` | Pick a random message ID between `base` and `max` (inclusive). |
| `0x67` | `SPACE` | 3 | `u8 width` | Inserts a blank space of `width` pixels. |
| `0x6A` | `MALE_FEMALE_CHECK` | 6 | `u16 m_msg, u16 f_msg` | Branch to `m_msg` if player is male, or `f_msg` if female. |
| `0x6B` | `GENDER_CHAR` | 4 | `u8 m_char, u8 f_char` | Inserts `m_char` if player is male, or `f_char` if female. |
| `0x71` | `PUT_STRING_ISLAND_NAME` | 2 | None | Inserts the player's island name. |
| `0x72` | `SET_CURSOR_JUST` | 2 | None | Sets "Just" mode: following text renders instantly without delay. |
| `0x73` | `CLR_CURSOR_JUST` | 2 | None | Clears "Just" mode: resumes character-by-character rendering. |
| `0x74` | `CUT_ARTICLE` | 2 | None | Prevents the next dynamic item string from including its article (a, an, the). |
| `0x75` | `CAPITAL_LETTER` | 2 | None | Forces the first character of the next dynamic string to be capitalized. |
| `0x76` | `PUT_STRING_AM_PM` | 2 | None | Inserts localized "AM" or "PM" string. |
| `0x77` | `SET_NEXT_MESSAGE_4` | 4 | `u16 msg_no` | Sets next message ID for choice 4. |
| `0x78` | `SET_NEXT_MESSAGE_5` | 4 | `u16 msg_no` | Sets next message ID for choice 5. |
| `0x79` | `SET_SELECT_STRING_5` | 12 | `u16 s1..s5` | Sets strings for 5 choices in the selection window. |
| `0x7A` | `SET_SELECT_STRING_6` | 14 | `u16 s1..s6` | Sets strings for 6 choices in the selection window. |

---

## Complex Code Details

### String Interpolation (`PUT_STRING_*`)
These codes are replaced in-place within the text buffer with the actual string content they represent. For example, `0x7F 0x1A` is deleted and replaced by the characters of the player's name.

### Dynamic Branching (`SET_NEXT_MESSAGE_*`)
These codes do not display anything. They update the `continue_msg_no` variable in the message window structure. When the current message finishes, the game checks this variable to see if another message should be loaded immediately.

- `SET_NEXT_MESSAGE_F` (0x0E): Always sets the next message.
- `SET_NEXT_MESSAGE_0-5` (0x0F-0x12, 0x77-0x78): Only sets the next message if the corresponding choice index (0-5) was selected in a previous selection window.
- `SET_NEXT_MESSAGE_RANDOM_*` (0x13-0x15, 0x63): Selects a random message ID from a set or range.

### Choice Setup (`SET_SELECT_STRING_*`)
These codes prepare the choice strings for a subsequent `SET_SELECT_WINDOW` (0x0D) call. They load localized strings from the ROM based on the provided IDs and store them in a temporary buffer. Up to 6 choices can be configured.

### Color Handling (`0x05` and `0x50`)
- `0x05` (COLOR): Changes the global text color for the remainder of the message or until changed again.
- `0x50` (SET_COLOR_CHAR): Uses a "counter" to apply a color to a specific number of characters, after which it reverts to the previous color. This is frequently used for highlighting the player's name in blue.

### Gender-Based Logic (`0x6A` and `0x6B`)
- `MALE_FEMALE_CHECK` (0x6A): Takes two 16-bit message IDs. Branches the conversation to the first if the player is male, and the second if female.
- `GENDER_CHAR` (0x6B): Takes two character bytes. Inserts the first if the player is male, and the second if female. This is commonly used for suffixes or gendered titles.

### Article Removal (`0x74` CUT_ARTICLE)
Animal Crossing's item strings often include the indefinite article (e.g., "a red snapper"). The `0x74` code sets the `mMsg_STATUS_FLAG_CUT_ARTICLE` flag. This tells the next dynamic string interpolation function (`mMsg_CopyItem` or `mMsg_CopyFree`) to skip copying the article prefix from the string resource. The flag is cleared immediately after use.

### Capitalization (`0x75` CAPITAL_LETTER)
Sets the `mMsg_STATUS_FLAG_CAPITALIZE` flag. The next dynamic string inserted will have its first character converted to uppercase via `mFont_small_to_capital`. This is useful when a dynamic string starts a sentence.

### Voice and Tone (`0x4B`-`0x4F`, `0x61`)
These codes change the NPC's "voice" synthesis tone (Normal, Angry, Sad, Fun, Sleepy, Gloomy). This affects the pitch and speed of the generated character sounds.

### Timing and Flow
- `0x03` (CURSOR_SET_TIME): The byte parameter is multiplied by 2.0 to account for the PC/GameCube version running at 60fps compared to the original N64 version's 30fps.
- `0x58` (MSG_TIME_END): The `time` parameter is bit-shifted and used to set an `end_timer`. When the timer expires, the message closes automatically without waiting for player input.
