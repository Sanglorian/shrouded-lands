---
layout: wiki_page
title: Template:StructuredQuote
pageid: 4173
namespace: 10
original_url: https://shrouded-lands.fandom.com/wiki/Template:StructuredQuote
categories: []
media: []
---
<blockquote class="pull-quote">
	<div class="pull-quote__text">{{{text|Text...}}}</div>

<cite>—{{{speaker|speaker}}}{{#if:{{{receiver|}}}|, to {{{receiver|}}}}}{{#if:{{{attribution|}}}|, {{{attribution|}}}}}{{#if:{{{source|}}}|, {{{source|}}}}}</cite>

</blockquote>
<noinclude>
# Description
A template used for displaying Structured Quotes ( ''<nowiki>{{#SQuote:}}</nowiki>'' ). If you want to unlock the full potential of Structured Quotes, please avoid using this template directly, and consider ''<nowiki>{{#SQuote:}}</nowiki>'' markup instead.
See https://community.fandom.com/wiki/Help:Structured_Quotes for extra information about Structured Quotes.

# Syntax
{{StructuredQuote
| text   =
| speaker =
| receiver =
| attribution =
| source  =
}}
</pre>

# Samples
{{StructuredQuote
|text=Size matters not. Look at me. Judge me by my size, do you? Hmm? Hmm. And well you should not. (...)
|speaker=Yoda
|receiver=Luke Skywalker
|source=Star Wars: Episode V The Empire Strikes Back
}}

{{StructuredQuote
|text=Size matters not. Look at me. Judge me by my size, do you? Hmm? Hmm. And well you should not. (...)
|speaker=Yoda
|receiver=Luke Skywalker
|source=Star Wars: Episode V The Empire Strikes Back
}}
</pre>

# TemplateData
<templatedata>
	{
		"params": {
			"text": {
				"label": "Quote text",
				"description": "quote text",
				"type": "content",
				"required": true
			},
			"speaker": {
				"label": "Person(s) quoted",
				"description": "individual(s) who uttered or wrote the quoted words (wikitext links, comma-separated)",
				"type": "content",
				"required": true
			},
			"receiver": {
				"label": "Person(s) to whom the quote was spoken",
				"description": "person the quote was spoken to (wikitext links, comma-separated)",
				"type": "content",
				"suggested": true
			},
			"attribution": {
				"label": "Attribution(s)",
				"description": "attribution (wikitext links, comma-separated)",
				"type": "content",
				"suggested": true
			},
			"source": {
				"label": "Quote source",
				"description": "place where it was spoken (wikitext link)",
				"type": "content",
				"suggested": true
			}
		},
		"format": "block"
	}
</templatedata>
</noinclude>
