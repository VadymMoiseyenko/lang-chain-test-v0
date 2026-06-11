import { useState } from "react";
import "./App.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function parseSseEvent(eventBlock) {
  const lines = eventBlock.split("\n");
  let eventName = "";
  const dataLines = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    }

    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (!eventName || dataLines.length === 0) {
    return null;
  }

  return {
    event: eventName,
    data: JSON.parse(dataLines.join("\n")),
  };
}

function App() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: "assistant",
      text: "Привіт! Постав питання про документи з цієї бази.",
      sources: [],
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();

    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isLoading) {
      return;
    }

    const userMessage = {
      id: Date.now(),
      role: "user",
      text: trimmedQuestion,
    };
    const assistantMessageId = Date.now() + 1;
    const assistantMessage = {
      id: assistantMessageId,
      role: "assistant",
      text: "",
      sources: [],
    };

    setMessages((currentMessages) => [
      ...currentMessages,
      userMessage,
      assistantMessage,
    ]);
    setQuestion("");
    setError("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/ask/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: trimmedQuestion }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || "Не вдалося отримати відповідь.");
      }

      if (!response.body) {
        throw new Error("Браузер не підтримує streaming response body.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let bufferedText = "";
      let streamedSources = [];
      let streamCompleted = false;

      while (!streamCompleted) {
        const { value, done } = await reader.read();

        if (done) {
          break;
        }

        bufferedText += decoder.decode(value, { stream: true });
        const eventBlocks = bufferedText.split("\n\n");
        bufferedText = eventBlocks.pop() || "";

        for (const eventBlock of eventBlocks) {
          const parsedEvent = parseSseEvent(eventBlock);

          if (!parsedEvent) {
            continue;
          }

          if (parsedEvent.event === "answer_chunk") {
            setMessages((currentMessages) =>
              currentMessages.map((message) =>
                message.id === assistantMessageId
                  ? {
                      ...message,
                      text: message.text + parsedEvent.data.content,
                    }
                  : message
              )
            );
          }

          if (parsedEvent.event === "sources") {
            streamedSources = parsedEvent.data.sources || [];
          }

          if (parsedEvent.event === "error") {
            throw new Error(parsedEvent.data.message || "Помилка під час стріму.");
          }

          if (parsedEvent.event === "done") {
            streamCompleted = true;
            setMessages((currentMessages) =>
              currentMessages.map((message) =>
                message.id === assistantMessageId
                  ? {
                      ...message,
                      sources: streamedSources,
                    }
                  : message
              )
            );
          }
        }
      }

      if (!streamCompleted) {
        setMessages((currentMessages) =>
          currentMessages.map((message) =>
            message.id === assistantMessageId
              ? {
                  ...message,
                  sources: streamedSources,
                }
              : message
          )
        );
      }
    } catch (requestError) {
      setMessages((currentMessages) =>
        currentMessages.filter((message) => message.id !== assistantMessageId)
      );
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="app">
      <section className="chat">
        <h1 className="title">Personal Docs Q&A Bot</h1>

        <div className="messages">
          {messages.map((message) => (
            <article
              key={message.id}
              className={`message message--${message.role}`}
            >
              <p className="message__role">
                {message.role === "user" ? "You" : "Bot"}
              </p>
              <p className="message__text">
                {message.text || (message.role === "assistant" ? "Думаю..." : "")}
              </p>

              {message.sources && message.sources.length > 0 ? (
                <div className="sources">
                  <p className="sources__title">Sources:</p>
                  <ul className="sources__list">
                    {message.sources.map((source, index) => (
                      <li key={`${source.source}-${index}`}>
                        {source.source}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </article>
          ))}
        </div>

        <form className="composer" onSubmit={handleSubmit}>
          <input
            className="composer__input"
            type="text"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Напиши питання про документи..."
            disabled={isLoading}
          />
          <button className="composer__button" type="submit" disabled={isLoading}>
            Send
          </button>
        </form>

        {error ? <p className="error">{error}</p> : null}
      </section>
    </main>
  );
}

export default App;
