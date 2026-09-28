<p align="center">
  <img src="assets/banner.svg" width="920" alt="send to instinct">
</p>

<p align="center">
  a tiny skill that hands the useful part of your coding-agent conversation over to instinct through imessage
</p>

<p align="center">
  <a href="https://skills.sh/MuaZahh/send-to-instinct"><img src="https://skills.sh/b/MuaZahh/send-to-instinct" alt="skills.sh installs"></a>
  <img src="https://img.shields.io/badge/mac_only-for_now-111827?style=flat-square" alt="mac only">
  <img src="https://img.shields.io/badge/dependencies-none-7c3aed?style=flat-square" alt="no dependencies">
  <img src="https://img.shields.io/badge/license-mit-06b6d4?style=flat-square" alt="mit license">
</p>

## install it everywhere

```sh
npx skills@latest add MuaZahh/send-to-instinct --all -g -y
```

that installs the skill globally for the coding agents the skills cli knows about — codex, claude code, cursor, and a whole bunch more.

then tell any of them:

```text
use $send-to-instinct to set up instinct with +1 555 123 4567
```

you can use instinct's apple id email instead of a phone number too. setup just pins the recipient; it doesn't send anything.

## how it works

```text
your conversation  →  one clean summary  →  messages.app  →  instinct
```

the agent takes the final decisions from the conversation, drops the rejected ideas and random back-and-forth, and sends one normal imessage to instinct.

there's intentionally not much more to it:

- it only sends to the one recipient you configured
- it doesn't read your messages
- it doesn't track instinct's task status
- it doesn't pretend instinct finished something just because the message was sent
- it doesn't resend automatically if the result is unclear

## a few examples

after comparing a bunch of products:

```text
$send-to-instinct buy the final keyboard parts we picked. no substitutions and keep it under $120.
```

after planning a build:

```text
$send-to-instinct send instinct the final parts list and ask it to add everything to my cart.
```

after researching suppliers:

```text
$send-to-instinct have instinct contact the three suppliers we shortlisted and ask for delivered prices.
```

or just:

```text
$send-to-instinct hand this over to instinct.
```

the agent uses the current conversation to figure out what "this" means and includes the useful links, limits, quantities, and other details.

## what gets stored

just the pinned phone number or apple id, locally at:

```text
~/Library/Application Support/SendToInstinct/config.json
```

the file is readable only by your mac user. messages themselves aren't copied into another database or log.

## what you need

- a mac with messages signed in
- python 3
- instinct's imessage phone number or apple id
- permission for your coding agent to automate messages when macos asks

## testing

```sh
python3 -m unittest discover -s tests -v
```

the tests use a fake messages runner. they won't text anyone.

## tiny disclaimer

this sends instructions; it doesn't verify what instinct does afterward. keep the wording clear when money, bookings, or messages to other people are involved.
