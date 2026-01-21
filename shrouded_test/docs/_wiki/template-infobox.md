---
layout: wiki_page
title: "Template:Infobox"
pageid: 1862
namespace: 10
original_url: "https://shrouded-lands.fandom.com/wiki/Template:Infobox"
categories:
  - "Category:General wiki templates"
  - "Category:Infobox templates"
media: []
---
<onlyinclude>{| class="wikia-infobox"

|-
! class="wikia-infobox-header" colspan="2" | {{{title|*Unknown*}}}

|-
{{#if: {{{image|}}} |
{{!}} class="wikia-infobox-image" colspan="2" {{!}} ![}}}](/media/{{{image}}})
| }}

|-
{{#if: {{{imagecaption|}}} |
{{!}} class="wikia-infobox-caption" colspan="2" {{!}} {{{imagecaption}}}
| }}

|- 
! colspan="2" | <div class="wikia-infobox-section-header">Some attributes</div>

|-
! First
| {{{first|*Unknown*}}}

|-
! Second
| {{{second|*Unknown*}}}

|-
! Third
| {{{third|*Unknown*}}}

|-
! colspan="2" | <div class="wikia-infobox-section-header">Other attributes</div>

|-
{{#if: {{{fourth|}}} |
! Fourth
{{!}} {{{fourth}}}
| }}

|-
{{#if: {{{fifth|}}} |
! Fifth
{{!}} {{{fifth}}}
| }}

|-
{{#if: {{{sixth|}}} |
! Sixth
{{!}} {{{sixth}}}
| }}

|- style="font-size:0; line-height:0;"
! style="width:50%; padding:0" |
! style="width:50%; padding:0" |

|}</onlyinclude><noinclude><br style="clear:both;"/>
{{documentation}}</noinclude>
