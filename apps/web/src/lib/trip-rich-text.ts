export type TripRichTextDocument = {
  type: "doc";
  content: TripRichTextBlock[];
};

export type TripRichTextBlock =
  | TripRichTextParagraph
  | TripRichTextHeading
  | TripRichTextList
  | TripRichTextCallout;

export type TripRichTextParagraph = {
  type: "paragraph";
  content: TripRichTextTextNode[];
};

export type TripRichTextHeading = {
  type: "heading";
  attrs: {
    level: 2 | 3;
  };
  content: TripRichTextTextNode[];
};

export type TripRichTextList = {
  type: "bullet_list" | "ordered_list";
  content: TripRichTextListItem[];
};

export type TripRichTextListItem = {
  type: "list_item";
  content: TripRichTextParagraph[];
};

export type TripRichTextCallout = {
  type: "callout";
  content: TripRichTextParagraph[];
};

export type TripRichTextTextNode = {
  type: "text";
  text: string;
  marks?: TripRichTextMark[];
};

export type TripRichTextMark =
  | { type: "bold" }
  | { type: "italic" }
  | { type: "link"; attrs: { href: string } };

export type TripRichTextRenderBlock =
  | {
      type: "paragraph";
      inlines: TripRichTextTextNode[];
    }
  | {
      type: "heading";
      level: 2 | 3;
      inlines: TripRichTextTextNode[];
    }
  | {
      type: "bullet_list" | "ordered_list";
      items: TripRichTextTextNode[][];
    }
  | {
      type: "callout";
      paragraphs: TripRichTextTextNode[][];
    };

export type TripRichTextEditableBlockType =
  | "paragraph"
  | "heading"
  | "bullet_list"
  | "ordered_list"
  | "callout";

export type TripRichTextEditableBlock = {
  id: string;
  type: TripRichTextEditableBlockType;
  text: string;
  bold: boolean;
  italic: boolean;
  linkHref: string;
};

const EMPTY_TRIP_RICH_TEXT: TripRichTextDocument = {
  type: "doc",
  content: [],
};

const ALLOWED_LINK_SCHEMES = new Set(["http", "https", "mailto", "tel"]);

export function emptyTripRichText(): TripRichTextDocument {
  return {
    type: "doc",
    content: [],
  };
}

export function normalizeTripRichText(value: unknown): TripRichTextDocument {
  if (!isRecord(value) || value.type !== "doc") {
    return emptyTripRichText();
  }

  const content = Array.isArray(value.content) ? value.content : [];
  const blocks = content
    .map((block) => normalizeBlock(block))
    .filter((block): block is TripRichTextBlock => block !== null);

  return {
    type: "doc",
    content: blocks,
  };
}

export function tripRichTextValidationErrors(value: unknown): string[] {
  if (!isRecord(value) || value.type !== "doc") {
    return ["Trip Rich Text must be a structured JSON document."];
  }

  if (!Array.isArray(value.content)) {
    return ["Trip Rich Text content must be a list."];
  }

  return [];
}

export function isTripRichTextEmpty(value: unknown): boolean {
  return getTripRichTextPlainText(normalizeTripRichText(value)).trim() === "";
}

export function getTripRichTextPlainText(value: unknown): string {
  const document = normalizeTripRichText(value);
  const parts: string[] = [];

  for (const block of document.content) {
    if (block.type === "paragraph" || block.type === "heading") {
      parts.push(inlinePlainText(block.content));
    } else if (block.type === "callout") {
      parts.push(...block.content.map((paragraph) => inlinePlainText(paragraph.content)));
    } else {
      parts.push(
        ...block.content.flatMap((item) =>
          item.content.map((paragraph) => inlinePlainText(paragraph.content)),
        ),
      );
    }
  }

  return parts.join(" ").replace(/\s+/g, " ").trim();
}

export function tripRichTextToRenderBlocks(value: unknown): TripRichTextRenderBlock[] {
  const document = normalizeTripRichText(value);

  return document.content.map((block) => {
    if (block.type === "paragraph") {
      return {
        type: "paragraph",
        inlines: block.content,
      };
    }

    if (block.type === "heading") {
      return {
        type: "heading",
        level: block.attrs.level,
        inlines: block.content,
      };
    }

    if (block.type === "callout") {
      return {
        type: "callout",
        paragraphs: block.content.map((paragraph) => paragraph.content),
      };
    }

    return {
      type: block.type,
      items: block.content.map((item) =>
        item.content.flatMap((paragraph, index) =>
          index === 0
            ? paragraph.content
            : [{ type: "text", text: " " } as TripRichTextTextNode, ...paragraph.content],
        ),
      ),
    };
  });
}

export function tripRichTextToEditableBlocks(
  value: unknown,
  createId: (index: number) => string = (index) => `description-block-${index + 1}`,
): TripRichTextEditableBlock[] {
  const document = normalizeTripRichText(value);
  const blocks = document.content.map((block, index) =>
    richTextBlockToEditableBlock(block, createId(index)),
  );

  return blocks.length > 0
    ? blocks
    : [newEditableTripRichTextBlock(createId(0), "paragraph")];
}

export function editableBlocksToTripRichText(
  blocks: TripRichTextEditableBlock[],
): TripRichTextDocument {
  const content = blocks
    .map((block) => editableBlockToRichTextBlock(block))
    .filter((block): block is TripRichTextBlock => block !== null);

  return {
    ...EMPTY_TRIP_RICH_TEXT,
    content,
  };
}

export function tripRichTextToHtml(value: unknown): string {
  const document = normalizeTripRichText(value);

  return document.content.map(richTextBlockToHtml).join("");
}

export function tiptapJsonToTripRichText(value: unknown): TripRichTextDocument {
  if (!isRecord(value) || value.type !== "doc") {
    return emptyTripRichText();
  }

  const content = Array.isArray(value.content) ? value.content : [];
  const blocks = content
    .flatMap((node) => tiptapNodeToBlocks(node))
    .filter((block): block is TripRichTextBlock => block !== null);

  return normalizeTripRichText({
    type: "doc",
    content: blocks,
  });
}

export function newEditableTripRichTextBlock(
  id: string,
  type: TripRichTextEditableBlockType = "paragraph",
): TripRichTextEditableBlock {
  return {
    id,
    type,
    text: "",
    bold: false,
    italic: false,
    linkHref: "",
  };
}

function normalizeBlock(value: unknown): TripRichTextBlock | null {
  if (!isRecord(value) || typeof value.type !== "string") {
    return null;
  }

  if (value.type === "paragraph") {
    const content = normalizeInlineContent(value.content);
    return content.length ? { type: "paragraph", content } : null;
  }

  if (value.type === "heading") {
    const content = normalizeInlineContent(value.content);
    if (!content.length) {
      return null;
    }
    const level = isRecord(value.attrs) && value.attrs.level === 3 ? 3 : 2;
    return {
      type: "heading",
      attrs: { level },
      content,
    };
  }

  if (value.type === "bullet_list" || value.type === "ordered_list") {
    const content = Array.isArray(value.content)
      ? value.content
          .map((item) => normalizeListItem(item))
          .filter((item): item is TripRichTextListItem => item !== null)
      : [];
    return content.length ? { type: value.type, content } : null;
  }

  if (value.type === "callout") {
    const content = Array.isArray(value.content)
      ? value.content
          .map((paragraph) => normalizeBlock(paragraph))
          .filter(
            (paragraph): paragraph is TripRichTextParagraph =>
              paragraph !== null && paragraph.type === "paragraph",
          )
      : [];
    return content.length ? { type: "callout", content } : null;
  }

  return null;
}

function normalizeListItem(value: unknown): TripRichTextListItem | null {
  if (!isRecord(value) || value.type !== "list_item" || !Array.isArray(value.content)) {
    return null;
  }

  const content = value.content
    .map((paragraph) => normalizeBlock(paragraph))
    .filter(
      (paragraph): paragraph is TripRichTextParagraph =>
        paragraph !== null && paragraph.type === "paragraph",
    );

  return content.length ? { type: "list_item", content } : null;
}

function normalizeInlineContent(value: unknown): TripRichTextTextNode[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((node) => normalizeTextNode(node))
    .filter((node): node is TripRichTextTextNode => node !== null);
}

function normalizeTextNode(value: unknown): TripRichTextTextNode | null {
  if (!isRecord(value) || value.type !== "text" || typeof value.text !== "string") {
    return null;
  }

  if (!value.text.trim()) {
    return null;
  }

  const marks = normalizeMarks(value.marks);
  return marks.length
    ? { type: "text", text: value.text, marks }
    : { type: "text", text: value.text };
}

function normalizeMarks(value: unknown): TripRichTextMark[] {
  if (!Array.isArray(value)) {
    return [];
  }

  const marks: TripRichTextMark[] = [];
  const seen = new Set<string>();

  for (const mark of value) {
    if (!isRecord(mark) || typeof mark.type !== "string") {
      continue;
    }

    if ((mark.type === "bold" || mark.type === "italic") && !seen.has(mark.type)) {
      marks.push({ type: mark.type });
      seen.add(mark.type);
    }

    if (mark.type === "link" && !seen.has("link")) {
      const href = isRecord(mark.attrs) && typeof mark.attrs.href === "string"
        ? sanitizeLinkHref(mark.attrs.href)
        : "";
      if (href) {
        marks.push({ type: "link", attrs: { href } });
        seen.add("link");
      }
    }
  }

  return marks;
}

function richTextBlockToEditableBlock(
  block: TripRichTextBlock,
  id: string,
): TripRichTextEditableBlock {
  const inlines =
    block.type === "paragraph" || block.type === "heading"
      ? block.content
      : block.type === "callout"
        ? block.content.flatMap((paragraph) => paragraph.content)
        : block.content.flatMap((item) =>
            item.content.flatMap((paragraph, index) => [
              ...(index > 0 ? [{ type: "text", text: "\n" } as TripRichTextTextNode] : []),
              ...paragraph.content,
            ]),
          );

  return {
    id,
    type: block.type,
    text:
      block.type === "bullet_list" || block.type === "ordered_list"
        ? block.content
            .map((item) =>
              item.content.map((paragraph) => inlinePlainText(paragraph.content)).join(" "),
            )
            .join("\n")
        : inlinePlainText(inlines),
    bold: inlines.some((inline) => hasMark(inline, "bold")),
    italic: inlines.some((inline) => hasMark(inline, "italic")),
    linkHref: inlines
      .flatMap((inline) => inline.marks ?? [])
      .find((mark): mark is Extract<TripRichTextMark, { type: "link" }> => mark.type === "link")
      ?.attrs.href ?? "",
  };
}

function editableBlockToRichTextBlock(
  block: TripRichTextEditableBlock,
): TripRichTextBlock | null {
  const text = block.text.trim();
  if (!text) {
    return null;
  }

  if (block.type === "bullet_list" || block.type === "ordered_list") {
    const items = text
      .split("\n")
      .map((line) => inlineTextNode(line.trim(), block))
      .filter((content) => content.length > 0)
      .map((content) => ({
        type: "list_item" as const,
        content: [{ type: "paragraph" as const, content }],
      }));
    return items.length ? { type: block.type, content: items } : null;
  }

  const paragraph = {
    type: "paragraph" as const,
    content: inlineTextNode(text, block),
  };

  if (!paragraph.content.length) {
    return null;
  }

  if (block.type === "paragraph") {
    return paragraph;
  }

  if (block.type === "heading") {
    return {
      type: "heading",
      attrs: { level: 2 },
      content: paragraph.content,
    };
  }

  return {
    type: "callout",
    content: [paragraph],
  };
}

function inlineTextNode(text: string, block: TripRichTextEditableBlock): TripRichTextTextNode[] {
  if (!text) {
    return [];
  }

  const marks: TripRichTextMark[] = [];
  if (block.bold) {
    marks.push({ type: "bold" });
  }
  if (block.italic) {
    marks.push({ type: "italic" });
  }
  const href = sanitizeLinkHref(block.linkHref);
  if (href) {
    marks.push({ type: "link", attrs: { href } });
  }

  return marks.length ? [{ type: "text", text, marks }] : [{ type: "text", text }];
}

function inlinePlainText(inlines: TripRichTextTextNode[]): string {
  return inlines.map((inline) => inline.text).join("");
}

function hasMark(inline: TripRichTextTextNode, markType: "bold" | "italic"): boolean {
  return (inline.marks ?? []).some((mark) => mark.type === markType);
}

function sanitizeLinkHref(value: string): string {
  const href = value.trim();
  const scheme = href.split(":", 1)[0]?.toLowerCase();
  if (!scheme || !ALLOWED_LINK_SCHEMES.has(scheme)) {
    return "";
  }

  try {
    const parsed = new URL(href);
    return parsed.href;
  } catch {
    return scheme === "mailto" || scheme === "tel" ? href : "";
  }
}

function richTextBlockToHtml(block: TripRichTextBlock): string {
  if (block.type === "paragraph") {
    return `<p>${richTextInlinesToHtml(block.content)}</p>`;
  }

  if (block.type === "heading") {
    const level = block.attrs.level;
    return `<h${level}>${richTextInlinesToHtml(block.content)}</h${level}>`;
  }

  if (block.type === "callout") {
    return `<blockquote>${block.content
      .map((paragraph) => `<p>${richTextInlinesToHtml(paragraph.content)}</p>`)
      .join("")}</blockquote>`;
  }

  const tag = block.type === "ordered_list" ? "ol" : "ul";
  const items = block.content
    .map((item) =>
      `<li>${item.content
        .map((paragraph) => `<p>${richTextInlinesToHtml(paragraph.content)}</p>`)
        .join("")}</li>`,
    )
    .join("");
  return `<${tag}>${items}</${tag}>`;
}

function richTextInlinesToHtml(inlines: TripRichTextTextNode[]): string {
  return inlines
    .map((inline) => {
      let text = escapeHtml(inline.text);

      for (const mark of inline.marks ?? []) {
        if (mark.type === "bold") {
          text = `<strong>${text}</strong>`;
        } else if (mark.type === "italic") {
          text = `<em>${text}</em>`;
        } else if (mark.type === "link") {
          text = `<a href="${escapeHtml(mark.attrs.href)}">${text}</a>`;
        }
      }

      return text;
    })
    .join("");
}

function tiptapNodeToBlocks(value: unknown): Array<TripRichTextBlock | null> {
  if (!isRecord(value) || typeof value.type !== "string") {
    return [];
  }

  if (value.type === "paragraph") {
    return [tiptapParagraphToRichText(value)];
  }

  if (value.type === "heading") {
    const content = tiptapInlineContent(value.content);
    if (!content.length) {
      return [];
    }
    const rawLevel = isRecord(value.attrs) ? value.attrs.level : 2;
    const level = rawLevel === 3 ? 3 : 2;
    return [{ type: "heading", attrs: { level }, content }];
  }

  if (value.type === "bulletList" || value.type === "orderedList") {
    const listType = value.type === "orderedList" ? "ordered_list" : "bullet_list";
    const items = Array.isArray(value.content)
      ? value.content
          .map((item) => tiptapListItemToRichText(item))
          .filter((item): item is TripRichTextListItem => item !== null)
      : [];
    return items.length ? [{ type: listType, content: items }] : [];
  }

  if (value.type === "blockquote") {
    const paragraphs = tiptapNestedParagraphs(value.content);
    return paragraphs.length ? [{ type: "callout", content: paragraphs }] : [];
  }

  if (value.type === "codeBlock") {
    const content = tiptapInlineContent(value.content);
    return content.length ? [{ type: "paragraph", content }] : [];
  }

  if (value.type === "table") {
    return tiptapTableToParagraphs(value);
  }

  if (Array.isArray(value.content)) {
    return value.content.flatMap((child) => tiptapNodeToBlocks(child));
  }

  return [];
}

function tiptapParagraphToRichText(value: Record<string, unknown>): TripRichTextParagraph | null {
  const content = tiptapInlineContent(value.content);
  return content.length ? { type: "paragraph", content } : null;
}

function tiptapListItemToRichText(value: unknown): TripRichTextListItem | null {
  if (!isRecord(value) || value.type !== "listItem") {
    return null;
  }

  const content = tiptapNestedParagraphs(value.content);
  return content.length ? { type: "list_item", content } : null;
}

function tiptapNestedParagraphs(value: unknown): TripRichTextParagraph[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .flatMap((child) => {
      if (!isRecord(child)) {
        return [];
      }

      if (child.type === "paragraph") {
        return [tiptapParagraphToRichText(child)];
      }

      return tiptapNestedParagraphs(child.content);
    })
    .filter((paragraph): paragraph is TripRichTextParagraph => paragraph !== null);
}

function tiptapTableToParagraphs(value: Record<string, unknown>): TripRichTextParagraph[] {
  if (!Array.isArray(value.content)) {
    return [];
  }

  return value.content
    .map((row) => {
      if (!isRecord(row) || row.type !== "tableRow" || !Array.isArray(row.content)) {
        return null;
      }

      const cellTexts = row.content
        .map((cell) =>
          isRecord(cell)
            ? getTripRichTextPlainText({
                type: "doc",
                content: tiptapNodeToBlocks(cell),
              })
            : "",
        )
        .filter(Boolean);
      const rowText = cellTexts.join(" | ");
      return rowText
        ? { type: "paragraph" as const, content: [{ type: "text" as const, text: rowText }] }
        : null;
    })
    .filter((paragraph): paragraph is TripRichTextParagraph => paragraph !== null);
}

function tiptapInlineContent(value: unknown): TripRichTextTextNode[] {
  if (!Array.isArray(value)) {
    return [];
  }

  const inlines: TripRichTextTextNode[] = [];

  for (const node of value) {
    if (!isRecord(node)) {
      continue;
    }

    if (node.type === "text" && typeof node.text === "string") {
      const textNode = tiptapTextNode(node);
      if (textNode) {
        inlines.push(textNode);
      }
      continue;
    }

    if (node.type === "hardBreak") {
      inlines.push({ type: "text", text: "\n" });
      continue;
    }

    inlines.push(...tiptapInlineContent(node.content));
  }

  return inlines;
}

function tiptapTextNode(value: Record<string, unknown>): TripRichTextTextNode | null {
  const text = typeof value.text === "string" ? value.text : "";
  if (!text.trim()) {
    return null;
  }

  const marks = tiptapMarks(value.marks);
  return marks.length ? { type: "text", text, marks } : { type: "text", text };
}

function tiptapMarks(value: unknown): TripRichTextMark[] {
  if (!Array.isArray(value)) {
    return [];
  }

  const marks: TripRichTextMark[] = [];
  const seen = new Set<string>();

  for (const mark of value) {
    if (!isRecord(mark) || typeof mark.type !== "string") {
      continue;
    }

    if ((mark.type === "bold" || mark.type === "italic") && !seen.has(mark.type)) {
      marks.push({ type: mark.type });
      seen.add(mark.type);
    }

    if (mark.type === "link" && !seen.has("link")) {
      const href = isRecord(mark.attrs) && typeof mark.attrs.href === "string"
        ? sanitizeLinkHref(mark.attrs.href)
        : "";
      if (href) {
        marks.push({ type: "link", attrs: { href } });
        seen.add("link");
      }
    }
  }

  return marks;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
