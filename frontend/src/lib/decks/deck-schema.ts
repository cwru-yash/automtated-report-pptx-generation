import { z } from "zod";

export type BlockType =
  | "heading"
  | "paragraph"
  | "bullet_list"
  | "ordered_list"
  | "quote"
  | "metric_card"
  | "table"
  | "chart_placeholder"
  | "image"
  | "two_column"
  | "three_column"
  | "callout"
  | "divider"
  | "footnote"
  | "source_note";

export type SlideLayoutType =
  | "title"
  | "executive_summary"
  | "context"
  | "finding"
  | "recommendation"
  | "limitation"
  | "appendix";

export type DeckTheme = {
  name: string;
  font_family: string;
  primary_color: string;
  accent_color: string;
  background_color: string;
  surface_color: string;
  text_color: string;
  muted_text_color: string;
};

export type DeckColumn = {
  width: number;
  content: ContentBlock[];
};

export type ContentBlock =
  | { id: string; type: "heading"; text: string; level: 1 | 2 | 3; metadata?: Record<string, unknown> }
  | { id: string; type: "paragraph"; text: string; metadata?: Record<string, unknown> }
  | { id: string; type: "bullet_list"; items: string[]; metadata?: Record<string, unknown> }
  | { id: string; type: "ordered_list"; items: string[]; metadata?: Record<string, unknown> }
  | { id: string; type: "quote"; text: string; metadata?: Record<string, unknown> }
  | { id: string; type: "metric_card"; label: string; value: string | number; helper?: string | null; metadata?: Record<string, unknown> }
  | { id: string; type: "table"; headers: string[]; rows: Array<Array<string | number>>; metadata?: Record<string, unknown> }
  | { id: string; type: "chart_placeholder"; chart_ref: string; title?: string | null; metadata?: Record<string, unknown> }
  | { id: string; type: "image"; src: string; alt?: string | null; metadata?: Record<string, unknown> }
  | { id: string; type: "two_column"; columns: [DeckColumn, DeckColumn]; metadata?: Record<string, unknown> }
  | { id: string; type: "three_column"; columns: [DeckColumn, DeckColumn, DeckColumn]; metadata?: Record<string, unknown> }
  | { id: string; type: "callout"; text: string; variant?: string | null; metadata?: Record<string, unknown> }
  | { id: string; type: "divider"; metadata?: Record<string, unknown> }
  | { id: string; type: "footnote"; text: string; metadata?: Record<string, unknown> }
  | { id: string; type: "source_note"; text: string; source?: string | null; metadata?: Record<string, unknown> };

export type DeckSlideDocument = {
  id: string;
  type: SlideLayoutType;
  title: string;
  speaker_notes: string;
  content: ContentBlock[];
  source_refs: string[];
};

export type DeckDocument = {
  deck_id: string;
  title: string;
  source_wave_id: string;
  source_project: string;
  theme: DeckTheme;
  slides: DeckSlideDocument[];
  metadata: Record<string, unknown>;
};

const metadataSchema = z.record(z.string(), z.unknown()).optional();

export const deckThemeSchema = z.object({
  name: z.string(),
  font_family: z.string(),
  primary_color: z.string(),
  accent_color: z.string(),
  background_color: z.string(),
  surface_color: z.string(),
  text_color: z.string(),
  muted_text_color: z.string(),
});

export const contentBlockSchema: z.ZodType<ContentBlock> = z.lazy(() =>
  z.discriminatedUnion("type", [
    z.object({ id: z.string(), type: z.literal("heading"), text: z.string(), level: z.union([z.literal(1), z.literal(2), z.literal(3)]), metadata: metadataSchema }),
    z.object({ id: z.string(), type: z.literal("paragraph"), text: z.string(), metadata: metadataSchema }),
    z.object({ id: z.string(), type: z.literal("bullet_list"), items: z.array(z.string()).min(1), metadata: metadataSchema }),
    z.object({ id: z.string(), type: z.literal("ordered_list"), items: z.array(z.string()).min(1), metadata: metadataSchema }),
    z.object({ id: z.string(), type: z.literal("quote"), text: z.string(), metadata: metadataSchema }),
    z.object({ id: z.string(), type: z.literal("metric_card"), label: z.string(), value: z.union([z.string(), z.number()]), helper: z.string().nullable().optional(), metadata: metadataSchema }),
    z.object({ id: z.string(), type: z.literal("table"), headers: z.array(z.string()).min(1), rows: z.array(z.array(z.union([z.string(), z.number()]))).min(1), metadata: metadataSchema }),
    z.object({ id: z.string(), type: z.literal("chart_placeholder"), chart_ref: z.string(), title: z.string().nullable().optional(), metadata: metadataSchema }),
    z.object({ id: z.string(), type: z.literal("image"), src: z.string(), alt: z.string().nullable().optional(), metadata: metadataSchema }),
    z.object({ id: z.string(), type: z.literal("two_column"), columns: z.tuple([deckColumnSchema, deckColumnSchema]), metadata: metadataSchema }),
    z.object({ id: z.string(), type: z.literal("three_column"), columns: z.tuple([deckColumnSchema, deckColumnSchema, deckColumnSchema]), metadata: metadataSchema }),
    z.object({ id: z.string(), type: z.literal("callout"), text: z.string(), variant: z.string().nullable().optional(), metadata: metadataSchema }),
    z.object({ id: z.string(), type: z.literal("divider"), metadata: metadataSchema }),
    z.object({ id: z.string(), type: z.literal("footnote"), text: z.string(), metadata: metadataSchema }),
    z.object({ id: z.string(), type: z.literal("source_note"), text: z.string(), source: z.string().nullable().optional(), metadata: metadataSchema }),
  ])
);

export const deckColumnSchema: z.ZodType<DeckColumn> = z.object({
  width: z.number().min(1).max(100),
  content: z.array(contentBlockSchema),
});

export const deckSlideDocumentSchema: z.ZodType<DeckSlideDocument> = z.object({
  id: z.string(),
  type: z.union([
    z.literal("title"),
    z.literal("executive_summary"),
    z.literal("context"),
    z.literal("finding"),
    z.literal("recommendation"),
    z.literal("limitation"),
    z.literal("appendix"),
  ]),
  title: z.string(),
  speaker_notes: z.string(),
  content: z.array(contentBlockSchema),
  source_refs: z.array(z.string()),
});

export const deckDocumentSchema: z.ZodType<DeckDocument> = z.object({
  deck_id: z.string(),
  title: z.string(),
  source_wave_id: z.string(),
  source_project: z.string(),
  theme: deckThemeSchema,
  slides: z.array(deckSlideDocumentSchema).min(1),
  metadata: z.record(z.string(), z.unknown()),
});

export type DeckProjectResponse = {
  id: string;
  source_wave_id: string;
  title: string;
  status: string;
  deck_json: DeckDocument;
  outline_json: Record<string, unknown>;
  theme_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};
