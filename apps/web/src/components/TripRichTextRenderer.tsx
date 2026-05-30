import type { ReactNode } from "react";

import {
  tripRichTextToRenderBlocks,
  type TripRichTextTextNode,
} from "@/lib/trip-rich-text";

export function TripRichTextRenderer({
  className = "trip-rich-text",
  document,
  emptyLabel = "Trip Description needed.",
}: {
  className?: string;
  document: unknown;
  emptyLabel?: string;
}) {
  const blocks = tripRichTextToRenderBlocks(document);

  if (blocks.length === 0) {
    return (
      <div className={`${className} is-empty`}>
        <p>{emptyLabel}</p>
      </div>
    );
  }

  return (
    <div className={className}>
      {blocks.map((block, blockIndex) => {
        if (block.type === "heading") {
          const HeadingTag = block.level === 3 ? "h3" : "h2";
          return (
            <HeadingTag key={`heading-${blockIndex}`}>
              {renderTripRichTextInlines(block.inlines)}
            </HeadingTag>
          );
        }

        if (block.type === "paragraph") {
          return <p key={`paragraph-${blockIndex}`}>{renderTripRichTextInlines(block.inlines)}</p>;
        }

        if (block.type === "callout") {
          return (
            <aside className="trip-rich-text-callout" key={`callout-${blockIndex}`}>
              {block.paragraphs.map((paragraph, paragraphIndex) => (
                <p key={`callout-paragraph-${paragraphIndex}`}>
                  {renderTripRichTextInlines(paragraph)}
                </p>
              ))}
            </aside>
          );
        }

        const ListTag = block.type === "ordered_list" ? "ol" : "ul";
        return (
          <ListTag key={`${block.type}-${blockIndex}`}>
            {block.items.map((item, itemIndex) => (
              <li key={`${block.type}-item-${itemIndex}`}>
                {renderTripRichTextInlines(item)}
              </li>
            ))}
          </ListTag>
        );
      })}
    </div>
  );
}

function renderTripRichTextInlines(inlines: TripRichTextTextNode[]) {
  return inlines.map((inline, index) => {
    let content: ReactNode = inline.text;

    for (const mark of inline.marks ?? []) {
      if (mark.type === "bold") {
        content = <strong>{content}</strong>;
      } else if (mark.type === "italic") {
        content = <em>{content}</em>;
      } else if (mark.type === "link") {
        content = (
          <a href={mark.attrs.href} rel="noreferrer noopener" target="_blank">
            {content}
          </a>
        );
      }
    }

    return <span key={`${inline.text}-${index}`}>{content}</span>;
  });
}
