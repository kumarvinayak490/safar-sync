"use client";

import type { CSSProperties } from "react";
import { useEffect, useRef, useState } from "react";
import { EditorContent, useEditor, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Link from "@tiptap/extension-link";
import Underline from "@tiptap/extension-underline";
import { TableKit } from "@tiptap/extension-table/kit";
import { Button, Form, Input, InputNumber, Popover, Space } from "antd";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Bold,
  Code,
  Italic,
  Link as LinkIcon,
  List,
  ListOrdered,
  Quote,
  RemoveFormatting,
  Strikethrough,
  Table as TableIcon,
  Trash2,
  Underline as UnderlineLucide,
} from "lucide-react";

const DEFAULT_HEIGHT = 280;
const ARTICLE_HEIGHT = 400;

export type RichTextEditorVariant = "default" | "article";

export interface RichTextEditorProps {
  value?: string | null;
  onChange?: (value: string) => void;
  onJsonChange?: (value: unknown) => void;
  placeholder?: string;
  readOnly?: boolean;
  style?: CSSProperties;
  /** Fixed height in px; content scrolls when it overflows. Default 280 (default variant) or 400 (article). */
  height?: number;
  /** Toolbar preset: "default" (compact) or "article" (headers, blockquote, code, link, table). */
  variant?: RichTextEditorVariant;
}

function Toolbar({
  editor,
  variant,
}: {
  editor: Editor | null;
  variant: RichTextEditorVariant;
}) {
  const [tablePopoverOpen, setTablePopoverOpen] = useState(false);
  const [linkPopoverOpen, setLinkPopoverOpen] = useState(false);
  const [tableForm] = Form.useForm();
  const [linkForm] = Form.useForm();

  if (!editor) return null;

  const disabled = !editor.isEditable;

  const onSetLink = (values: { url: string }) => {
    if (values.url) {
      editor.chain().focus().setLink({ href: values.url }).run();
    } else {
      editor.chain().focus().unsetLink().run();
    }
    setLinkPopoverOpen(false);
    linkForm.resetFields();
  };

  const onInsertTable = (values: { rows: number; cols: number }) => {
    editor
      .chain()
      .focus()
      .insertTable({ rows: values.rows, cols: values.cols, withHeaderRow: true })
      .run();
    setTablePopoverOpen(false);
    tableForm.resetFields();
  };

  const linkContent = (
    <Form
      form={linkForm}
      layout="vertical"
      initialValues={{ url: editor.getAttributes("link").href }}
      onFinish={onSetLink}
      style={{ width: 220 }}
    >
      <Form.Item
        label="URL"
        name="url"
        rules={[{ type: "url", message: "Please enter a valid URL" }]}
        style={{ marginBottom: 12 }}
      >
        <Input placeholder="https://example.com" size="small" />
      </Form.Item>
      <Form.Item style={{ marginBottom: 0 }}>
        <Space style={{ width: "100%", justifyContent: "flex-end" }}>
          <Button
            size="small"
            danger
            onClick={() => {
              editor.chain().focus().unsetLink().run();
              setLinkPopoverOpen(false);
            }}
          >
            Remove
          </Button>
          <Button type="primary" htmlType="submit" size="small">
            Apply
          </Button>
        </Space>
      </Form.Item>
    </Form>
  );

  const tableContent = (
    <Form
      form={tableForm}
      layout="vertical"
      initialValues={{ rows: 3, cols: 3 }}
      onFinish={onInsertTable}
      style={{ width: 150 }}
    >
      <Form.Item label="Rows" name="rows" style={{ marginBottom: 8 }}>
        <InputNumber min={1} max={10} style={{ width: "100%" }} />
      </Form.Item>
      <Form.Item label="Columns" name="cols" style={{ marginBottom: 12 }}>
        <InputNumber min={1} max={10} style={{ width: "100%" }} />
      </Form.Item>
      <Form.Item style={{ marginBottom: 0 }}>
        <Button type="primary" htmlType="submit" block size="small">
          Insert
        </Button>
      </Form.Item>
    </Form>
  );

  return (
    <div className="rich-text-toolbar">
      <div className="rich-text-toolbar-group">
        <select
          value={editor.getAttributes("heading").level || ""}
          onChange={(event) => {
            const value = event.target.value;
            if (value === "1") editor.chain().focus().toggleHeading({ level: 1 }).run();
            else if (value === "2") editor.chain().focus().toggleHeading({ level: 2 }).run();
            else if (value === "3") editor.chain().focus().toggleHeading({ level: 3 }).run();
            else editor.chain().focus().setParagraph().run();
          }}
          className="rich-text-toolbar-select"
          disabled={disabled}
        >
          <option value="">Normal</option>
          <option value="1">Heading 1</option>
          <option value="2">Heading 2</option>
          <option value="3">Heading 3</option>
        </select>
      </div>
      <div className="rich-text-toolbar-group">
        <button
          type="button"
          disabled={disabled}
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={editor.isActive("bold") ? "is-active" : ""}
          title="Bold"
        >
          <Bold size={16} className="rich-text-toolbar-icon" />
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={editor.isActive("italic") ? "is-active" : ""}
          title="Italic"
        >
          <Italic size={16} className="rich-text-toolbar-icon" />
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          className={editor.isActive("underline") ? "is-active" : ""}
          title="Underline"
        >
          <UnderlineLucide size={16} className="rich-text-toolbar-icon" />
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => editor.chain().focus().toggleStrike().run()}
          className={editor.isActive("strike") ? "is-active" : ""}
          title="Strikethrough"
        >
          <Strikethrough size={16} className="rich-text-toolbar-icon" />
        </button>
      </div>
      <div className="rich-text-toolbar-group">
        <button
          type="button"
          disabled={disabled}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={editor.isActive("bulletList") ? "is-active" : ""}
          title="Bullet list"
        >
          <List size={16} className="rich-text-toolbar-icon" />
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={editor.isActive("orderedList") ? "is-active" : ""}
          title="Numbered list"
        >
          <ListOrdered size={16} className="rich-text-toolbar-icon" />
        </button>
      </div>
      <div className="rich-text-toolbar-group">
        <Popover
          content={linkContent}
          title="Set Link"
          trigger="click"
          open={linkPopoverOpen}
          onOpenChange={(open) => {
            if (disabled) return;
            setLinkPopoverOpen(open);
            if (open) {
              linkForm.setFieldsValue({ url: editor.getAttributes("link").href });
            }
          }}
          placement="bottom"
        >
          <button
            type="button"
            disabled={disabled}
            className={editor.isActive("link") ? "is-active" : ""}
            title="Link"
          >
            <LinkIcon size={16} className="rich-text-toolbar-icon" />
          </button>
        </Popover>
      </div>
      <div className="rich-text-toolbar-group">
        <Popover
          content={tableContent}
          title="Insert Table"
          trigger="click"
          open={tablePopoverOpen}
          onOpenChange={(open) => {
            if (!disabled) setTablePopoverOpen(open);
          }}
          placement="bottom"
        >
          <button
            type="button"
            disabled={disabled}
            className={editor.isActive("table") ? "is-active" : ""}
            title="Insert table"
          >
            <TableIcon size={16} className="rich-text-toolbar-icon" />
          </button>
        </Popover>
      </div>
      {editor.isActive("table") && (
        <div className="rich-text-toolbar-group">
          <button type="button" disabled={disabled} onClick={() => editor.chain().focus().addRowBefore().run()} title="Add row above" className="table-op">
            <ArrowUp size={14} className="rich-text-toolbar-icon" /> Row up
          </button>
          <button type="button" disabled={disabled} onClick={() => editor.chain().focus().addRowAfter().run()} title="Add row below" className="table-op">
            <ArrowDown size={14} className="rich-text-toolbar-icon" /> Row down
          </button>
          <button type="button" disabled={disabled} onClick={() => editor.chain().focus().deleteRow().run()} title="Delete row" className="table-op table-op-delete">
            <Trash2 size={14} className="rich-text-toolbar-icon" /> Row
          </button>
          <button type="button" disabled={disabled} onClick={() => editor.chain().focus().addColumnBefore().run()} title="Add column before" className="table-op">
            <ArrowLeft size={14} className="rich-text-toolbar-icon" /> Col left
          </button>
          <button type="button" disabled={disabled} onClick={() => editor.chain().focus().addColumnAfter().run()} title="Add column after" className="table-op">
            <ArrowRight size={14} className="rich-text-toolbar-icon" /> Col right
          </button>
          <button type="button" disabled={disabled} onClick={() => editor.chain().focus().deleteColumn().run()} title="Delete column" className="table-op table-op-delete">
            <Trash2 size={14} className="rich-text-toolbar-icon" /> Col
          </button>
          <button
            type="button"
            disabled={disabled}
            onClick={() => editor.chain().focus().deleteTable().run()}
            title="Delete table"
            className="table-op table-op-delete"
          >
            <Trash2 size={14} className="rich-text-toolbar-icon" /> Table
          </button>
        </div>
      )}
      {variant === "article" && (
        <div className="rich-text-toolbar-group">
          <button
            type="button"
            disabled={disabled}
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            className={editor.isActive("blockquote") ? "is-active" : ""}
            title="Blockquote"
          >
            <Quote size={16} className="rich-text-toolbar-icon" />
          </button>
          <button
            type="button"
            disabled={disabled}
            onClick={() => editor.chain().focus().toggleCodeBlock().run()}
            className={editor.isActive("codeBlock") ? "is-active" : ""}
            title="Code block"
          >
            <Code size={16} className="rich-text-toolbar-icon" />
          </button>
        </div>
      )}
      <div className="rich-text-toolbar-group">
        <button type="button" disabled={disabled} onClick={() => editor.chain().focus().unsetAllMarks().clearNodes().run()} title="Clear format">
          <RemoveFormatting size={16} className="rich-text-toolbar-icon" />
        </button>
      </div>
    </div>
  );
}

export function RichTextEditor({
  value,
  onChange,
  onJsonChange,
  placeholder = "Write here...",
  readOnly = false,
  style,
  height,
  variant = "default",
}: RichTextEditorProps) {
  const resolvedHeight = height ?? (variant === "article" ? ARTICLE_HEIGHT : DEFAULT_HEIGHT);
  const lastEmittedRef = useRef<string>(value ?? "");
  const isInternalUpdateRef = useRef(false);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3, 4, 5, 6] },
        link: false,
      }),
      Placeholder.configure({ placeholder }),
      Link.configure({ openOnClick: false }),
      Underline,
      TableKit,
    ],
    content: value ?? "",
    editable: !readOnly,
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class: "rich-text-editor-content",
      },
    },
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      isInternalUpdateRef.current = true;
      lastEmittedRef.current = html;
      onChange?.(html);
      onJsonChange?.(editor.getJSON());
    },
  });

  useEffect(() => {
    editor?.setEditable(!readOnly);
  }, [editor, readOnly]);

  useEffect(() => {
    if (!editor) return;
    const nextValue = value ?? "";
    if (isInternalUpdateRef.current) {
      isInternalUpdateRef.current = false;
      return;
    }
    if (nextValue !== lastEmittedRef.current) {
      lastEmittedRef.current = nextValue;
      editor.commands.setContent(nextValue, { emitUpdate: false });
    }
  }, [editor, value]);

  if (!editor) return null;

  return (
    <div
      className="rich-text-editor-fixed"
      style={{ height: `${resolvedHeight}px`, ...style }}
    >
      <Toolbar editor={editor} variant={variant} />
      <div
        className="rich-text-editor-scroll"
        onClick={() => {
          if (!editor.isFocused && editor.isEditable) {
            editor.commands.focus();
          }
        }}
      >
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}
