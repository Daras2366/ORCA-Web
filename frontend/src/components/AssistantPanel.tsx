import { useEffect, useRef, useState, type ReactNode } from "react";
import { Loader2, MapPin, Mic, MicOff, RotateCcw, Send, Volume2, VolumeX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { OrcaLogo } from "./OrcaLogo";
import { suggestedQuestions } from "@/data/mockData";
import { useLocationContext } from "@/hooks/useLocation";
import { useMapLocate } from "@/hooks/useMapLocate";
import { extractZoneIds } from "@/lib/zoneIds";
import { createConversationId, queryAssistant } from "@/services/assistantService";
import type { ChatMessage } from "@/types/marine";

// Lines that are purely a heading label for a zone (no data value on the same line).
// A button is deferred for these and emitted after the full response instead.
const HEADING_LINE_RE =
  /^(?:distance to|route to|route safety for|ocean conditions at|safety at|conditions at|pfz zone|zone)\s+(PFZ\d{4}|GRID_\d{4})\s*$/i;

/** Returns true when a line is a standalone heading label containing a zone ID
 *  (e.g. "Distance to PFZ0006") and should NOT get an inline button. */
function isHeadingLine(line: string): boolean {
  return HEADING_LINE_RE.test(line.trim());
}

/** Renders assistant message text line-by-line, placing a Locate button
 *  immediately beneath each line that mentions a known map zone ID.
 *  Heading-only lines are excluded from inline buttons; their IDs are
 *  collected and a single button block is emitted at the end instead. */
function renderInlineMarkdown(text: string): ReactNode[] {
  const parts = text.split(/(\*\*.*?\*\*)/g);

  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      const boldText = part.slice(2, -2);

      if (boldText.trim().toUpperCase() === "CAUTION") {
        return (
          <strong key={index} className="font-semibold text-warn">
            CAUTION
          </strong>
        );
      }

      return (
        <strong key={index} className="font-semibold text-shell">
          {boldText}
        </strong>
      );
    }

    return <span key={index}>{part}</span>;
  });
}

function AssistantMessageBody({ content }: { content: string }) {
  const { locateZone, availableZoneIds } = useMapLocate();
  const lines = content.split("\n");

  // Collect zone IDs from heading-only lines.
  const deferredIds = new Set<string>();

  for (const line of lines) {
    if (isHeadingLine(line)) {
      for (const id of extractZoneIds(line)) {
        if (availableZoneIds.has(id)) {
          deferredIds.add(id);
        }
      }
    }
  }

  return (
    <div className="space-y-2">
      {lines.map((line, i) => {
        const trimmed = line.trim();

        // Preserve completely blank lines without creating huge gaps.
        if (!trimmed) {
          return <div key={i} className="h-1" />;
        }

        const heading = isHeadingLine(trimmed);

        const idsInLine = heading
          ? []
          : [...new Set(extractZoneIds(trimmed).filter((id) => availableZoneIds.has(id)))];

        // Markdown bullet
        const isBullet = /^[-*]\s+/.test(trimmed);
        const bulletText = isBullet ? trimmed.replace(/^[-*]\s+/, "") : trimmed;

        // Markdown numbered list
        const numberedMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);

        return (
          <div key={i} className="leading-6">
            {isBullet ? (
              <div className="flex gap-2">
                <span className="shrink-0">•</span>
                <span>{renderInlineMarkdown(bulletText)}</span>
              </div>
            ) : numberedMatch ? (
              <div className="flex gap-2">
                <span className="shrink-0">{numberedMatch[1]}.</span>
                <span>{renderInlineMarkdown(numberedMatch[2] ?? "")}</span>
              </div>
            ) : (
              <span>{renderInlineMarkdown(trimmed)}</span>
            )}

            {idsInLine.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-2">
                {idsInLine.map((zoneId) => (
                  <Button
                    key={zoneId}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-7 gap-1.5 text-xs"
                    onClick={() => locateZone(zoneId)}
                  >
                    <MapPin className="size-3.5" />
                    Locate on map
                  </Button>
                ))}
              </div>
            )}
          </div>
        );
      })}

      {deferredIds.size > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {[...deferredIds].map((zoneId) => (
            <Button
              key={zoneId}
              type="button"
              variant="outline"
              size="sm"
              className="h-7 gap-1.5 text-xs"
              onClick={() => locateZone(zoneId)}
            >
              <MapPin className="size-3.5" />
              Locate on map
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}

export function AssistantPanel() {
  const { location } = useLocationContext();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [ttsLoadingId, setTtsLoadingId] = useState<string | null>(null);
  const [speakingId, setSpeakingId] = useState<string | null>(null);

  const voiceSupported =
    typeof window !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== "undefined";

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  const conversationId = useRef(createConversationId());
  const scrollRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();

      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
      }
    };
  }, []);

  const transcribeAudio = async (audioBlob: Blob) => {
    setTranscribing(true);
    setError(null);

    try {
      const formData = new FormData();

      formData.append("file", audioBlob, "orca-voice.webm");

      const response = await fetch("http://127.0.0.1:8001/transcribe", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);

        throw new Error(body?.detail || "Voice transcription failed.");
      }

      const data = await response.json();

      if (!data.text) {
        throw new Error("No speech was detected.");
      }

      setInput(data.text);
    } catch (err) {
      console.error("ORCA transcription error:", err);

      setError(err instanceof Error ? err.message : "Voice transcription failed.");
    } finally {
      setTranscribing(false);
    }
  };

  const speakResponse = async (messageId: string, text: string) => {
    // If this response is currently playing, stop it.
    if (speakingId === messageId) {
      audioRef.current?.pause();

      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = null;
      }

      audioRef.current = null;
      setSpeakingId(null);
      return;
    }

    // Stop any previous audio.
    audioRef.current?.pause();

    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }

    setTtsLoadingId(messageId);
    setSpeakingId(null);
    setError(null);

    try {
      const response = await fetch("http://127.0.0.1:8001/synthesize", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);

        throw new Error(body?.detail || "Speech synthesis failed.");
      }

      const audioBlob = await response.blob();

      if (!audioBlob.size) {
        throw new Error("No audio was returned.");
      }

      const audioUrl = URL.createObjectURL(audioBlob);

      audioUrlRef.current = audioUrl;

      const audio = new Audio(audioUrl);

      audioRef.current = audio;

      audio.onended = () => {
        setSpeakingId(null);

        if (audioUrlRef.current) {
          URL.revokeObjectURL(audioUrlRef.current);
          audioUrlRef.current = null;
        }

        audioRef.current = null;
      };

      audio.onerror = () => {
        setSpeakingId(null);
        setError("Could not play the ORCA voice response.");

        if (audioUrlRef.current) {
          URL.revokeObjectURL(audioUrlRef.current);
          audioUrlRef.current = null;
        }

        audioRef.current = null;
      };

      setTtsLoadingId(null);
      setSpeakingId(messageId);

      await audio.play();
    } catch (err) {
      console.error("ORCA TTS error:", err);

      setTtsLoadingId(null);
      setSpeakingId(null);

      setError(err instanceof Error ? err.message : "Speech synthesis failed.");
    }
  };

  const toggleVoiceInput = async () => {
    if (loading || transcribing) {
      return;
    }

    // If already recording, stop the recording.
    if (isListening) {
      mediaRecorderRef.current?.stop();
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Your browser does not support microphone recording.");
      return;
    }

    if (!window.isSecureContext) {
      setError("Voice input requires HTTPS or localhost.");
      return;
    }

    try {
      setError(null);

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      const mimeTypes = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"];

      const supportedMimeType = mimeTypes.find((type) => MediaRecorder.isTypeSupported(type));

      const recorder = supportedMimeType
        ? new MediaRecorder(stream, {
            mimeType: supportedMimeType,
          })
        : new MediaRecorder(stream);

      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstart = () => {
        console.log("ORCA Voice: microphone recording started");

        setIsListening(true);
        setError(null);
      };

      recorder.onstop = async () => {
        console.log("ORCA Voice: microphone recording stopped");

        setIsListening(false);

        // Stop microphone access.
        stream.getTracks().forEach((track) => track.stop());

        const audioBlob = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });

        audioChunksRef.current = [];

        if (audioBlob.size === 0) {
          setError("No audio was recorded.");
          return;
        }

        await transcribeAudio(audioBlob);
      };

      recorder.onerror = () => {
        console.error("ORCA Voice: MediaRecorder error");

        setIsListening(false);

        stream.getTracks().forEach((track) => track.stop());

        setError("Microphone recording failed. Please try again.");
      };

      mediaRecorderRef.current = recorder;

      recorder.start();
    } catch (err) {
      console.error("ORCA microphone error:", err);

      setIsListening(false);

      if (err instanceof DOMException) {
        if (err.name === "NotAllowedError") {
          setError("Microphone permission was denied. Please allow microphone access.");
          return;
        }

        if (err.name === "NotFoundError") {
          setError("No microphone was found.");
          return;
        }

        if (err.name === "NotReadableError") {
          setError("The microphone is being used by another application.");
          return;
        }
      }

      setError("Could not start microphone recording.");
    }
  };

  const send = async (text: string) => {
    const value = text.trim();
    if (!value || loading) return;
    setInput("");
    setError(null);
    setMessages((prev) => [
      ...prev,
      { id: `${Date.now()}-u`, role: "user", content: value, createdAt: Date.now() },
    ]);
    setLoading(true);
    try {
      const res = await queryAssistant(value, location, conversationId.current);
      setMessages((prev) => [
        ...prev,
        { id: `${Date.now()}-a`, role: "assistant", content: res.reply, createdAt: Date.now() },
      ]);
    } catch {
      setError("ORCA could not answer that right now. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const clear = () => {
    setMessages([]);
    setError(null);
    conversationId.current = createConversationId();
  };

  return (
    <div className="flex h-full min-h-0 flex-col border-l border-border bg-card">
      <div className="flex items-start justify-between gap-2 border-b border-border px-4 py-4">
        <div className="flex items-start gap-3">
          <OrcaLogo className="size-8 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-shell">ORCA AI Assistant</p>
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="size-1.5 rounded-full bg-safe" /> Online
            </p>
          </div>
        </div>
        {messages.length > 0 && (
          <Button variant="ghost" size="icon" onClick={clear} title="Clear conversation">
            <RotateCcw className="size-4" />
            <span className="sr-only">Clear conversation</span>
          </Button>
        )}
      </div>

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div>
            <h3 className="text-base font-semibold text-shell">Ask ORCA</h3>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              Get insights on fishing zones, ocean conditions, safety and more.
            </p>
            <div className="mt-4 space-y-2">
              {suggestedQuestions.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => send(q)}
                  className="w-full rounded-lg border border-border bg-deep px-3 py-2 text-left text-xs text-blush transition-colors hover:border-rose hover:text-shell"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-4">
          {messages.map((m) =>
            m.role === "user" ? (
              <div key={m.id} className="flex justify-end">
                <p className="max-w-[85%] rounded-xl rounded-br-sm bg-primary px-3 py-2 text-sm text-primary-foreground">
                  {m.content}
                </p>
              </div>
            ) : (
              <div key={m.id} className="flex gap-2">
                <OrcaLogo className="mt-0.5 size-5 shrink-0" />

                <div className="max-w-[92%] text-sm leading-6 text-shell">
                  <AssistantMessageBody content={m.content} />

                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="mt-1 h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-shell"
                    onClick={() => speakResponse(m.id, m.content)}
                    disabled={ttsLoadingId !== null && ttsLoadingId !== m.id}
                    title={
                      speakingId === m.id
                        ? "Stop speaking"
                        : ttsLoadingId === m.id
                          ? "Generating speech..."
                          : "Listen to response"
                    }
                  >
                    {ttsLoadingId === m.id ? (
                      <>
                        <Loader2 className="size-3.5 animate-spin" />
                        Generating voice...
                      </>
                    ) : speakingId === m.id ? (
                      <>
                        <VolumeX className="size-3.5" />
                        Stop
                      </>
                    ) : (
                      <>
                        <Volume2 className="size-3.5" />
                        Listen
                      </>
                    )}
                  </Button>
                </div>
              </div>
            ),
          )}

          {loading && (
            <p className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="size-3.5 animate-spin" /> ORCA is thinking…
            </p>
          )}
          {error && <p className="text-xs text-danger">{error}</p>}
        </div>
      </div>

      <div className="border-t border-border px-4 py-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="flex items-end gap-2"
        >
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            placeholder={
              isListening
                ? "Listening..."
                : transcribing
                  ? "Transcribing..."
                  : "Type your question..."
            }
            rows={2}
            className="min-h-[44px] resize-none bg-deep text-sm"
          />

          {voiceSupported && (
            <Button
              type="button"
              size="icon"
              variant={isListening ? "default" : "outline"}
              className="size-10 shrink-0"
              onClick={toggleVoiceInput}
              disabled={loading || transcribing}
              title={
                transcribing ? "Transcribing..." : isListening ? "Stop recording" : "Voice input"
              }
            >
              {transcribing ? (
                <Loader2 className="size-4 animate-spin" />
              ) : isListening ? (
                <MicOff className="size-4" />
              ) : (
                <Mic className="size-4" />
              )}

              <span className="sr-only">
                {transcribing
                  ? "Transcribing"
                  : isListening
                    ? "Stop voice recording"
                    : "Start voice input"}
              </span>
            </Button>
          )}

          <Button
            type="submit"
            size="icon"
            className="size-10 shrink-0"
            disabled={loading || !input.trim()}
          >
            <Send className="size-4" />
            <span className="sr-only">Send</span>
          </Button>
        </form>

        <p className="mt-2 flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <MapPin className="size-3" />
          Using your location for more accurate results
        </p>
      </div>
    </div>
  );
}
