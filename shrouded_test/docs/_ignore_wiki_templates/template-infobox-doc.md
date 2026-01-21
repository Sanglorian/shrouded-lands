---
layout: wiki_page
title: "Template:Infobox/doc"
pageid: 1938
namespace: 10
original_url: "https://shrouded-lands.fandom.com/wiki/Template:Infobox/doc"
categories:
  - "Category:Template documentation"
media: []
---

==Description==
This template is a sample infobox, to aid in the creation of new infoboxes.

Recommended usage: copy the template code to a new template page, and edit it there.

===Infobox and template background===
See [[Help:Templates]], [[Help:Infobox]] and [[Help:Tables]] for some background on how templates and infoboxes work.

===Building blocks===
The infobox is made of the following basic building blocks:

* Overall table class: <code>class="wikia-infobox"</code>
* Table heading cell class: <code>class="wikia-infobox-header"</code>
* Use row header marks ("<code>!</code>") for row title cells ''(and "<code>|</code>" for normal cells)''
* Section separator line: give the header below it a wrapping <code>div</code> with <code>class="wikia-infobox-section-header"</code>
* Image cell class: <code>class="wikia-infobox-image"</code>
* Image caption cell class: <code>class="wikia-infobox-caption"</code>

===Other notes===
* The Title, First, Second, and Third rows show ''"Unknown"'' if their values are not specified.
* The Image, Imagecaption, Fourth, Fifth, and Sixth rows won't show up if their values are not specified: they are each completely enclosed in an 'if' statement.

==Syntax==
<pre>
{{infobox
 | title         = 
 | image         = [e.g. "Example.jpg"]
 | imagewidth    = [e.g. "150"] [default: 210 pixels]
 | imagecaption  = 
 | first         =
 | second        =
 | third         =
 | fourth        =
 | fifth         =
 | sixth         =
}}
</pre>

==Samples==
<pre>
{{infobox
 | title         = A pretty flower
 | image         = Example.jpg
 | imagewidth    = 100
 | imagecaption  = Floweris flowerum
 | first         = Pink and green
 | second        = Outdoors
 | fourth        = Annual
}}
</pre>

Results in...

{{infobox
 | title         = A pretty flower
 | image         = Example.jpg
 | imagewidth    = 100
 | imagecaption  = Floweris flowerum
 | first         = Pink and green
 | second        = Outdoors
 | fourth        = Annual
}}

<includeonly>[[Category:General wiki templates|{{PAGENAME}}]][[Category:Infobox templates| ]]</includeonly><noinclude>[[Category:Template documentation|{{PAGENAME}}]]</noinclude>
