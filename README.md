<p align="center">
  <img src="assets/banner.svg" width="920" alt="text instinct">
</p>

a tiny skill for handing the useful part of a coding-agent conversation over to instinct through imessage.

## install

```sh
npx skills@latest add MuaZahh/text-instinct --all -g -y
```

this installs it globally for codex, claude code, cursor, and other compatible coding agents.

## set it up once

tell your agent:

```text
use $text-instinct to set up instinct
```

the skill searches contacts for exact-name `instinct` candidates and shows you a masked phone number or email. you confirm the right one once, then it pins that exact imessage handle.

if it finds nothing, give it the phone number or apple id shown in your instinct imessage conversation. macos asks for contacts and messages access on first use, not during installation. if messages was closed before sending, the helper closes it again afterward.

## use it

after comparing some products:

```text
$text-instinct buy the final ones we picked. no substitutions and keep it under $120.
```

after planning a build:

```text
$text-instinct send instinct the final parts list and ask it to add everything to my cart.
```

after researching suppliers:

```text
$text-instinct have instinct contact the three suppliers we shortlisted and ask for delivered prices.
```

or simply:

```text
$text-instinct hand this over to instinct.
```

the agent turns the final decision, useful links, quantities, and limits into one normal message. it reports whether that message was sent; it doesn't claim to know what instinct does afterward.

## requirements

macos, python 3, and messages signed into imessage.

## license

mit
