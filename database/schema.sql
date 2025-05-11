CREATE TABLE public.speakers (
    id text NOT NULL PRIMARY KEY,
    name text NOT NULL UNIQUE,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.utterances (
    id uuid NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    speaker_id text NOT NULL,
    start_time real NOT NULL,
    end_time real NOT NULL,
    transcript text NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);
CREATE TABLE public.words (
    id uuid NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    speaker_id text NULL,
    utterance_id uuid NULL,
    word text NOT NULL,
    start_time real NOT NULL,
    end_time real NOT NULL,
    pos_tag text NULL,
    lemma text NULL,
    sentiment_score real NULL,
    embedding vector(128) NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);
ALTER TABLE public.words ADD CONSTRAINT words_speaker_id_fkey FOREIGN KEY (speaker_id) REFERENCES public.speakers(id) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE public.words ADD CONSTRAINT words_utterance_id_fkey FOREIGN KEY (utterance_id) REFERENCES public.utterances(id) ON UPDATE RESTRICT ON DELETE RESTRICT;