
import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8001";
const API_PORT = new URL(API_BASE_URL).port || (new URL(API_BASE_URL).protocol === "https:" ? "443" : "80");

function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hello. I am JARVIS, your personal AI assistant. My local AI engine is ready. How may I assist you today?",
    },
  ]);
  const [memoryInput, setMemoryInput] = useState("");
  const [memoryTitle, setMemoryTitle] = useState("");
  const [memoryCategory, setMemoryCategory] = useState("general");
  const [memoryList, setMemoryList] = useState([]);
  const [editingMemoryId, setEditingMemoryId] = useState(null);
  const [savingMemory, setSavingMemory] = useState(false);
  const [engineStatus, setEngineStatus] = useState(null);
  const [engineModel, setEngineModel] = useState("");
  const [engineLoading, setEngineLoading] = useState(true);
  const [engineSaving, setEngineSaving] = useState(false);
  const [engineError, setEngineError] = useState("");
  const [voiceListening, setVoiceListening] = useState(false);
  const [voiceOutput, setVoiceOutput] = useState(false);
  const [voiceRate, setVoiceRate] = useState(1);
  const [voiceList, setVoiceList] = useState([]);
  const [voiceName, setVoiceName] = useState("");
  const [voiceError, setVoiceError] = useState("");
  const [notes, setNotes] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [dueReminders, setDueReminders] = useState([]);
  const [notificationPermission, setNotificationPermission] = useState(
    () => window.Notification?.permission || "unsupported"
  );
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [noteSearchQuery, setNoteSearchQuery] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [reminderTitle, setReminderTitle] = useState("");
  const [reminderTime, setReminderTime] = useState("");
  const [productivityError, setProductivityError] = useState("");
  const [actionCommand, setActionCommand] = useState("");
  const [actionPreview, setActionPreview] = useState(null);
  const [actionResult, setActionResult] = useState("");
  const [actionError, setActionError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [weatherLocation, setWeatherLocation] = useState("");
  const [weatherResult, setWeatherResult] = useState(null);
  const [githubRepository, setGithubRepository] = useState("");
  const [githubResult, setGithubResult] = useState(null);
  const [onlineError, setOnlineError] = useState("");
  const [systemStatus, setSystemStatus] = useState(null);
  const [systemError, setSystemError] = useState("");
  const [loading, setLoading] = useState(false);
  const [activePage, setActivePage] = useState("Assistant");
  const recognitionRef = useRef(null);
  const notifiedReminderIds = useRef(new Set());

  useEffect(() => {
    if (notificationPermission !== "granted" || !window.Notification) return;
    dueReminders.forEach((reminder) => {
      if (notifiedReminderIds.current.has(reminder.id)) return;
      new Notification("JARVIS reminder", { body: reminder.title });
      notifiedReminderIds.current.add(reminder.id);
    });
  }, [dueReminders, notificationPermission]);

  const refreshSystemStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/system/status`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load system status.");
      setSystemStatus(data);
      setSystemError("");
    } catch (error) {
      setSystemError(error.message);
    }
  };

  useEffect(() => {
    let isMounted = true;

    const loadConversation = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/history`);

        if (!response.ok) {
          throw new Error("Could not load saved conversation.");
        }

        const data = await response.json();

        if (isMounted && data.messages.length > 0) {
          const savedMessages = data.messages.map((item) => ({
            role: item.role,
            text: item.content,
          }));

          setMessages(savedMessages);
        }
      } catch (error) {
        console.error("Memory loading error:", error);
      }
    };

    const loadMemories = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/memory`);

        if (!response.ok) {
          throw new Error("Could not load saved memories.");
        }

        const data = await response.json();

        if (isMounted) {
          setMemoryList(data.memories || []);
        }
      } catch (error) {
        console.error("Failed to load memory list:", error);
      }
    };

    const loadEngineStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/engine`);

        if (!response.ok) {
          throw new Error("Could not load local engine status.");
        }

        const data = await response.json();
        if (isMounted) {
          setEngineStatus(data);
          setEngineModel(data.model || "");
          setEngineError("");
        }
      } catch (error) {
        if (isMounted) {
          setEngineStatus({ connected: false, models: [] });
          setEngineError(error.message);
        }
      } finally {
        if (isMounted) {
          setEngineLoading(false);
        }
      }
    };

    const loadSystemStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/system/status`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Could not load system status.");
        if (isMounted) {
          setSystemStatus(data);
          setSystemError("");
        }
      } catch (error) {
        if (isMounted) setSystemError(error.message);
      }
    };

    const loadProductivity = async () => {
      try {
        const [notesResponse, tasksResponse, remindersResponse, dueResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/notes`),
          fetch(`${API_BASE_URL}/tasks`),
          fetch(`${API_BASE_URL}/reminders`),
          fetch(`${API_BASE_URL}/reminders/due`),
        ]);
        if (![notesResponse, tasksResponse, remindersResponse, dueResponse].every((response) => response.ok)) {
          throw new Error("Could not load notes, tasks, and reminders.");
        }
        const [notesData, tasksData, remindersData, dueData] = await Promise.all([
          notesResponse.json(),
          tasksResponse.json(),
          remindersResponse.json(),
          dueResponse.json(),
        ]);
        if (isMounted) {
          setNotes(notesData.notes || []);
          setTasks(tasksData.tasks || []);
          setReminders(remindersData.reminders || []);
          setDueReminders(dueData.reminders || []);
        }
      } catch (error) {
        if (isMounted) setProductivityError(error.message);
      }
    };

    loadConversation();
    loadMemories();
    loadEngineStatus();
    loadProductivity();
    loadSystemStatus();

    const reminderTimer = window.setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/reminders/due`);
        if (!response.ok) return;
        const data = await response.json();
        if (isMounted) setDueReminders(data.reminders || []);
      } catch (error) {
        console.error("Reminder check failed:", error);
      }
    }, 60000);

    return () => {
      isMounted = false;
      window.clearInterval(reminderTimer);
    };
  }, []);

  useEffect(() => {
    if (!window.speechSynthesis) {
      return undefined;
    }

    const updateVoices = () => setVoiceList(window.speechSynthesis.getVoices());
    updateVoices();
    window.speechSynthesis.addEventListener("voiceschanged", updateVoices);

    return () => {
      window.speechSynthesis.removeEventListener("voiceschanged", updateVoices);
      window.speechSynthesis.cancel();
    };
  }, []);

  const updateEngineModel = async (event) => {
    event.preventDefault();

    if (!engineModel || engineSaving) {
      return;
    }

    setEngineSaving(true);
    setEngineError("");

    try {
      const response = await fetch(`${API_BASE_URL}/engine/model`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ model: engineModel }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Could not change the local model.");
      }

      const data = await response.json();
      setEngineStatus(data);
      setEngineModel(data.model);
    } catch (error) {
      setEngineError(error.message);
    } finally {
      setEngineSaving(false);
    }
  };

  const saveMemory = async (event) => {
    event.preventDefault();
    const trimmedMemory = memoryInput.trim();

    if (!trimmedMemory || savingMemory) {
      return;
    }

    setSavingMemory(true);

    try {
      const response = await fetch(
        editingMemoryId
          ? `${API_BASE_URL}/memory/${editingMemoryId}`
          : `${API_BASE_URL}/memory`,
        {
        method: editingMemoryId ? "PUT" : "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: memoryTitle.trim() || "memory",
          category: memoryCategory.trim() || "general",
          content: trimmedMemory,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Could not save memory.");
      }

      const data = await response.json();
      setMemoryList((previous) => editingMemoryId
        ? previous.map((memory) => memory.id === editingMemoryId ? data.memory : memory)
        : [data.memory, ...previous.filter((memory) => memory.id !== data.memory.id)]);
      setMemoryInput("");
      setMemoryTitle("");
      setMemoryCategory("general");
      setEditingMemoryId(null);
    } catch (error) {
      console.error("Failed to save memory:", error);
    } finally {
      setSavingMemory(false);
    }
  };

  const deleteMemory = async (memoryId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/memory/${memoryId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Could not delete memory.");
      }

      setMemoryList((previous) => previous.filter((memory) => memory.id !== memoryId));
    } catch (error) {
      console.error("Failed to delete memory:", error);
    }
  };

  const sendChatText = async (text) => {
    const trimmedMessage = text.trim();

    if (!trimmedMessage || loading) return;

    setMessages((previous) => [
      ...previous,
      { role: "user", text: trimmedMessage },
    ]);

    setMessage("");
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: trimmedMessage,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || "The JARVIS backend returned an error."
        );
      }

      const data = await response.json();

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          text: data.reply || "I received an empty response.",
        },
      ]);
      if (voiceOutput && window.speechSynthesis) {
        const utterance = new SpeechSynthesisUtterance(data.reply || "I received an empty response.");
        utterance.rate = voiceRate;
        utterance.voice = voiceList.find((voice) => voice.name === voiceName) || null;
        window.speechSynthesis.speak(utterance);
      }
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          text: "I could not connect to my AI engine. Please check that the JARVIS backend and Ollama are running.",
        },
      ]);

      console.error("JARVIS connection error:", error);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = (event) => {
    event.preventDefault();
    sendChatText(message);
  };

  const startVoiceInput = () => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setVoiceError("Speech recognition is not supported by this browser.");
      return;
    }

    setVoiceError("");
    const recognition = new Recognition();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onstart = () => setVoiceListening(true);
    recognition.onerror = (event) => {
      setVoiceError(event.error === "not-allowed"
        ? "Microphone permission was denied. Allow microphone access and try again."
        : `Speech recognition failed: ${event.error}.`);
    };
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript?.trim();
      if (transcript) {
        setMessage(transcript);
        sendChatText(transcript);
      }
    };
    recognition.onend = () => {
      setVoiceListening(false);
      recognitionRef.current = null;
    };
    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch (error) {
      recognitionRef.current = null;
      setVoiceListening(false);
      setVoiceError(`Could not start microphone input: ${error.message}`);
    }
  };

  const stopVoiceInput = () => recognitionRef.current?.stop();

  const stopSpeechOutput = () => window.speechSynthesis?.cancel();

  const enableReminderNotifications = async () => {
    if (!window.Notification) {
      setNotificationPermission("unsupported");
      return;
    }
    const permission = await window.Notification.requestPermission();
    setNotificationPermission(permission);
  };

  const createNoteHandler = async (event) => {
    event.preventDefault();
    try {
      const response = await fetch(`${API_BASE_URL}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: noteTitle, content: noteContent }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not save note.");
      setNotes((previous) => [data.note, ...previous]);
      setNoteTitle("");
      setNoteContent("");
      setProductivityError("");
    } catch (error) {
      setProductivityError(error.message);
    }
  };

  const createTaskHandler = async (event) => {
    event.preventDefault();
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: taskTitle }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not create task.");
      setTasks((previous) => [data.task, ...previous]);
      setTaskTitle("");
      setProductivityError("");
    } catch (error) {
      setProductivityError(error.message);
    }
  };

  const searchSavedNotes = async (event) => {
    event.preventDefault();
    try {
      const response = await fetch(
        `${API_BASE_URL}/notes/search?query=${encodeURIComponent(noteSearchQuery)}`
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not search saved notes.");
      setNotes(data.notes || []);
      setProductivityError("");
    } catch (error) {
      setProductivityError(error.message);
    }
  };

  const completeTask = async (task) => {
    try {
      const status = task.status === "completed" ? "pending" : "completed";
      const response = await fetch(`${API_BASE_URL}/tasks/${task.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not update task.");
      setTasks((previous) => previous.map((item) => item.id === task.id ? data.task : item));
    } catch (error) {
      setProductivityError(error.message);
    }
  };

  const createReminderHandler = async (event) => {
    event.preventDefault();
    try {
      const response = await fetch(`${API_BASE_URL}/reminders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: reminderTitle,
          remind_at: new Date(reminderTime).toISOString(),
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not set reminder.");
      setReminders((previous) => [...previous, data.reminder]);
      setReminderTitle("");
      setReminderTime("");
      setProductivityError("");
    } catch (error) {
      setProductivityError(error.message || "Choose a valid reminder date and time.");
    }
  };

  const acknowledgeReminder = async (reminderId, action) => {
    try {
      const response = await fetch(`${API_BASE_URL}/reminders/${reminderId}/${action}`, {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not update reminder.");
      setDueReminders((previous) => previous.filter((item) => item.id !== reminderId));
      setReminders((previous) => previous.map((item) => item.id === reminderId ? data.reminder : item));
    } catch (error) {
      setProductivityError(error.message);
    }
  };

  const previewDesktopAction = async (event) => {
    event.preventDefault();
    setActionPreview(null);
    setActionResult("");
    setActionError("");
    try {
      const response = await fetch(`${API_BASE_URL}/automation/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: actionCommand }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "That action is not available.");
      setActionPreview(data);
    } catch (error) {
      setActionError(error.message);
    }
  };

  const executeDesktopAction = async () => {
    if (!actionPreview) return;
    try {
      const response = await fetch(`${API_BASE_URL}/automation/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          preview_id: actionPreview.preview_id,
          confirmed: true,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not execute action.");
      setActionResult(Array.isArray(data.result) ? data.result.join("\n") : data.result);
      setActionPreview(null);
      setActionCommand("");
    } catch (error) {
      setActionError(error.message);
      setActionPreview(null);
    }
  };

  const searchWeb = async (event) => {
    event.preventDefault();
    setOnlineError("");
    try {
      const response = await fetch(`${API_BASE_URL}/search?query=${encodeURIComponent(searchQuery)}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Web search failed.");
      setSearchResults(data.results || []);
    } catch (error) {
      setOnlineError(error.message);
    }
  };

  const lookupWeather = async (event) => {
    event.preventDefault();
    setOnlineError("");
    try {
      const response = await fetch(`${API_BASE_URL}/integrations/weather?location=${encodeURIComponent(weatherLocation)}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Weather lookup failed.");
      setWeatherResult(data);
    } catch (error) {
      setOnlineError(error.message);
    }
  };

  const lookupGithub = async (event) => {
    event.preventDefault();
    setOnlineError("");
    const [owner, repository] = githubRepository.split("/").map((part) => part.trim());
    if (!owner || !repository || githubRepository.split("/").length !== 2) {
      setOnlineError("Enter a public repository as owner/repository.");
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/integrations/github/${encodeURIComponent(owner)}/${encodeURIComponent(repository)}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "GitHub lookup failed.");
      setGithubResult(data);
    } catch (error) {
      setOnlineError(error.message);
    }
  };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">J</div>
          <div>
            <h2>JARVIS</h2>
            <span>AI SYSTEM</span>
          </div>
        </div>

        <div className="nav-section">
          <p className="nav-label">WORKSPACE</p>

          {["Overview", "Assistant", "Memory", "System"].map((page) => (
            <button
              key={page}
              className={`nav-item ${activePage === page ? "active" : ""}`}
              onClick={() => setActivePage(page)}
            >
              <span className="nav-icon">
                {page === "Overview" && "◫"}
                {page === "Assistant" && "◉"}
                {page === "Memory" && "▤"}
                {page === "System" && "⚙"}
              </span>
              {page}
            </button>
          ))}
        </div>

        <div className="sidebar-bottom">
          <div className="connection-card">
            <span className="status-dot"></span>
            <div>
              <strong>Local AI Engine</strong>
              <small>Connection configured</small>
            </div>
          </div>

          <button
            className="nav-item settings-button"
            onClick={() => setActivePage("Settings")}
          >
            <span className="nav-icon">⚙</span>
            Settings
          </button>

          <div className="user-profile">
            <div className="user-avatar">S</div>
            <div>
              <strong>Administrator</strong>
              <small>Local user</small>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="breadcrumb">JARVIS / {activePage}</p>
            <h1>{activePage}</h1>
          </div>

          <div className="topbar-status">
            <span className="status-dot"></span>
            SYSTEM ONLINE
          </div>
        </header>

        <section className="dashboard-content">
          <div className="welcome-section">
            <div>
              <p className="eyebrow">PERSONAL AI ASSISTANT</p>
              <h2>Good to see you.</h2>
              <p className="welcome-description">
                Your personal intelligence system is ready to assist.
              </p>
            </div>

            <div className="date-card">
              <span>AI ENGINE</span>
              <strong>{engineStatus?.model || "Local model"}</strong>
              <small>{engineStatus?.model_available ? "Installed · Local model" : "Model status unavailable"}</small>
            </div>
          </div>

          <div className="status-grid">
            <div className="status-card">
              <div className="card-top">
                <span>AI ENGINE</span>
                <span className="card-symbol">◉</span>
              </div>
              <h3>Ollama</h3>
              <p><span className="status-dot"></span> {engineStatus?.connected ? "Connected" : "Unavailable"}</p>
            </div>

            <div className="status-card">
              <div className="card-top">
                <span>BACKEND API</span>
                <span className="card-symbol">⌘</span>
              </div>
              <h3>FastAPI</h3>
              <p><span className="status-dot"></span> Port {API_PORT}</p>
            </div>

            <div className="status-card">
              <div className="card-top">
                <span>INTERFACE</span>
                <span className="card-symbol">▣</span>
              </div>
              <h3>React + Vite</h3>
              <p><span className="status-dot"></span> Port 5173</p>
            </div>
          </div>

          <section className="system-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">SYSTEM OVERVIEW</p>
                <h2>{systemStatus?.system || "Local system"}</h2>
              </div>
              <button type="button" className="voice-button secondary" onClick={refreshSystemStatus}>
                Refresh
              </button>
            </div>
            {systemStatus ? (
              <div className="system-metrics">
                <div><span>Platform</span><strong>{systemStatus.platform}</strong></div>
                <div><span>CPU cores</span><strong>{systemStatus.cpu_count ?? "Unavailable"}</strong></div>
                <div>
                  <span>Memory</span>
                  <strong>
                    {systemStatus.memory
                      ? `${(systemStatus.memory.available_bytes / 1024 ** 3).toFixed(1)} GB free of ${(systemStatus.memory.total_bytes / 1024 ** 3).toFixed(1)} GB`
                      : "Unavailable"}
                  </strong>
                  {systemStatus.memory && <progress max="100" value={systemStatus.memory.used_percent} />}
                </div>
                <div>
                  <span>Home disk</span>
                  <strong>{`${systemStatus.disk.used_percent}% used · ${(systemStatus.disk.free_bytes / 1024 ** 3).toFixed(1)} GB free`}</strong>
                  <progress max="100" value={systemStatus.disk.used_percent} />
                </div>
                <div><span>Uptime</span><strong>{systemStatus.uptime_seconds == null ? "Unavailable" : `${Math.floor(systemStatus.uptime_seconds / 3600)}h ${Math.floor((systemStatus.uptime_seconds % 3600) / 60)}m`}</strong></div>
                <div><span>Load average</span><strong>{systemStatus.load_average?.map((value) => value.toFixed(2)).join(" / ") || "Unavailable"}</strong></div>
              </div>
            ) : (
              <p className="system-error" role="status">{systemError || "Loading system metrics..."}</p>
            )}
            {systemError && systemStatus && <p className="system-error" role="alert">{systemError}</p>}
          </section>

          <section className="engine-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">LOCAL MODEL RUNTIME</p>
                <h2>Engine management</h2>
              </div>
              <span
                className={`engine-state ${engineStatus?.connected ? "connected" : "disconnected"}`}
                aria-live="polite"
              >
                <span className="status-dot"></span>
                {engineLoading ? "CHECKING" : engineStatus?.status || "UNAVAILABLE"}
              </span>
            </div>

            <div className="engine-body">
              <p className="engine-description">
                {engineStatus?.connected
                  ? `Active model: ${engineStatus.model}`
                  : "Ollama is unavailable. Start the local service to manage models."}
              </p>
              <form className="engine-controls" onSubmit={updateEngineModel}>
                <label htmlFor="engine-model">Installed model</label>
                <select
                  id="engine-model"
                  value={engineModel}
                  onChange={(event) => setEngineModel(event.target.value)}
                  disabled={engineLoading || !engineStatus?.connected || engineSaving}
                >
                  {!engineModel && <option value="">Select a model</option>}
                  {engineModel && !engineStatus?.models?.includes(engineModel) && (
                    <option value={engineModel} disabled>
                      {engineModel} (not installed)
                    </option>
                  )}
                  {(engineStatus?.models || []).map((model) => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                </select>
                <button
                  type="submit"
                  disabled={
                    engineLoading ||
                    engineSaving ||
                    !engineStatus?.connected ||
                    !engineModel ||
                    engineModel === engineStatus?.model
                  }
                >
                  {engineSaving ? "Applying..." : "Use Model"}
                </button>
              </form>
              {engineError && <p className="engine-error" role="alert">{engineError}</p>}
            </div>
          </section>

          <section className="assistant-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">INTERACTIVE CONSOLE</p>
                <h2>JARVIS Assistant</h2>
              </div>

              <span className="model-badge">LOCAL AI</span>
            </div>

            <div className="chat-area">
              <div className="chat-visual">
                <div className="visualizer-ring ring-one"></div>
                <div className="visualizer-ring ring-two"></div>
                <div className="visualizer-ring ring-three"></div>
                <div className="visualizer-core">J</div>
              </div>

              <div className="chat-messages">
                {messages.map((item, index) => (
                  <div key={index} className={`message ${item.role}`}>
                    <div className="message-avatar">
                      {item.role === "assistant" ? "J" : "S"}
                    </div>

                    <div className="message-content">
                      <span>{item.role === "assistant" ? "JARVIS" : "YOU"}</span>
                      <p>{item.text}</p>
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="message assistant">
                    <div className="message-avatar">J</div>
                    <div className="message-content">
                      <span>JARVIS</span>
                      <p className="thinking">Processing your request...</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <section className="voice-controls" aria-label="Voice controls">
              <div className="voice-input-controls">
                <button
                  type="button"
                  className="voice-button"
                  onClick={voiceListening ? stopVoiceInput : startVoiceInput}
                  disabled={loading}
                >
                  {voiceListening ? "Stop listening" : "Start listening"}
                </button>
                <span>{voiceListening ? "Listening for one request" : "Microphone is off"}</span>
              </div>
              <div className="voice-output-controls">
                <button
                  type="button"
                  className="voice-button secondary"
                  onClick={() => setVoiceOutput((enabled) => !enabled)}
                  aria-pressed={voiceOutput}
                >
                  {voiceOutput ? "Mute replies" : "Speak replies"}
                </button>
                <label htmlFor="speech-voice">Voice</label>
                <select
                  id="speech-voice"
                  value={voiceName}
                  onChange={(event) => setVoiceName(event.target.value)}
                  disabled={!voiceList.length}
                >
                  <option value="">System default</option>
                  {voiceList.map((voice) => (
                    <option key={`${voice.name}-${voice.lang}`} value={voice.name}>
                      {voice.name} ({voice.lang})
                    </option>
                  ))}
                </select>
                <label htmlFor="speech-rate">Speed</label>
                <input
                  id="speech-rate"
                  type="range"
                  min="0.7"
                  max="1.3"
                  step="0.1"
                  value={voiceRate}
                  onChange={(event) => setVoiceRate(Number(event.target.value))}
                />
                <button type="button" className="voice-button secondary" onClick={stopSpeechOutput}>
                  Stop speech
                </button>
              </div>
              <p className="voice-note">
                Voice input is push-to-listen. Browser recognition availability and audio processing vary by browser.
              </p>
              {voiceError && <p className="engine-error" role="alert">{voiceError}</p>}
            </section>

            <section className="action-controls" aria-label="Approved desktop actions">
              <div>
                <p className="eyebrow">APPROVED DESKTOP ACTIONS</p>
                <h3>Computer controls</h3>
              </div>
              <form className="action-form" onSubmit={previewDesktopAction}>
                <input
                  value={actionCommand}
                  onChange={(event) => setActionCommand(event.target.value)}
                  placeholder="Open VS Code, file info report.pdf, organize file report.pdf"
                  maxLength="500"
                  required
                />
                <button type="submit">Preview</button>
              </form>
              {actionPreview && (
                <div className="action-preview" role="status">
                  <p>{actionPreview.display}</p>
                  <span>{actionPreview.requires_confirmation ? "Confirmation required" : "Read-only action"}</span>
                  <button type="button" onClick={executeDesktopAction}>
                    {actionPreview.requires_confirmation ? "Confirm and run" : "Run"}
                  </button>
                  <button type="button" className="action-cancel" onClick={() => setActionPreview(null)}>Cancel</button>
                </div>
              )}
              {actionResult && <pre className="action-result">{actionResult}</pre>}
              {actionError && <p className="engine-error" role="alert">{actionError}</p>}
              <p className="voice-note">Only predefined actions are supported. JARVIS does not execute arbitrary terminal commands or modify files.</p>
            </section>

            <form className="chat-input-area" onSubmit={sendMessage}>
              <input
                type="text"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Ask JARVIS anything..."
                disabled={loading}
              />

              <button type="submit" disabled={loading || !message.trim()}>
                {loading ? "..." : "SEND ↗"}
              </button>
            </form>

            <p className="input-note">
              <span className="status-dot"></span>
              Messages are processed using your local AI engine.
            </p>
          </section>

          <section className="memory-panel">
            <div className="panel-header memory-header">
              <div>
                <p className="eyebrow">PERSONAL MEMORY</p>
                <h2>Saved facts and preferences</h2>
              </div>
            </div>

            <div className="memory-body">
              <form className="memory-form" onSubmit={saveMemory}>
                <input
                  type="text"
                  value={memoryTitle}
                  onChange={(event) => setMemoryTitle(event.target.value)}
                  placeholder="Memory title"
                />
                <input
                  type="text"
                  value={memoryCategory}
                  onChange={(event) => setMemoryCategory(event.target.value)}
                  placeholder="Category"
                />
                <textarea
                  value={memoryInput}
                  onChange={(event) => setMemoryInput(event.target.value)}
                  placeholder="Save a fact or preference for JARVIS..."
                  rows="3"
                />
                <button type="submit" disabled={savingMemory || !memoryInput.trim()}>
                  {savingMemory ? "Saving..." : editingMemoryId ? "Update Memory" : "Save Memory"}
                </button>
                {editingMemoryId && (
                  <button
                    type="button"
                    onClick={() => {
                      setEditingMemoryId(null);
                      setMemoryInput("");
                      setMemoryTitle("");
                      setMemoryCategory("general");
                    }}
                  >
                    Cancel edit
                  </button>
                )}
              </form>

              <div className="memory-list">
                {memoryList.length === 0 ? (
                  <div className="memory-empty">
                    No saved memories yet. JARVIS will remember useful facts here.
                  </div>
                ) : (
                  memoryList.map((memory) => (
                    <div key={memory.id} className="memory-item">
                      <div className="memory-item-top">
                        <strong>{memory.title || "Memory"}</strong>
                        <span>{memory.category || "general"}</span>
                      </div>
                      <p>{memory.content}</p>
                      <button type="button" onClick={() => {
                        setEditingMemoryId(memory.id);
                        setMemoryTitle(memory.title || "");
                        setMemoryCategory(memory.category || "general");
                        setMemoryInput(memory.content);
                      }}>
                        Edit
                      </button>
                      <button type="button" onClick={() => deleteMemory(memory.id)}>
                        Delete
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </section>

          <section className="productivity-panel">
            <div className="panel-header memory-header">
              <div>
                <p className="eyebrow">PERSONAL WORKSPACE</p>
                <h2>Notes, tasks and reminders</h2>
              </div>
            </div>
            <div className="productivity-grid">
              <section className="productivity-section">
                <h3>Notes</h3>
                <form className="productivity-form" onSubmit={createNoteHandler}>
                  <input value={noteTitle} onChange={(event) => setNoteTitle(event.target.value)} placeholder="Note title" required maxLength="160" />
                  <textarea value={noteContent} onChange={(event) => setNoteContent(event.target.value)} placeholder="Write a note" required maxLength="5000" rows="3" />
                  <button type="submit">Save note</button>
                </form>
                <form className="note-search-form" onSubmit={searchSavedNotes}>
                  <input
                    value={noteSearchQuery}
                    onChange={(event) => setNoteSearchQuery(event.target.value)}
                    placeholder="Search saved notes"
                    required
                    maxLength="200"
                  />
                  <button type="submit">Search</button>
                  <button
                    type="button"
                    onClick={async () => {
                      setNoteSearchQuery("");
                      const response = await fetch(`${API_BASE_URL}/notes`);
                      const data = await response.json();
                      setNotes(data.notes || []);
                    }}
                  >
                    All
                  </button>
                </form>
                <ul className="productivity-list">
                  {notes.map((note) => <li key={note.id}><strong>{note.title}</strong><p>{note.content}</p></li>)}
                </ul>
              </section>

              <section className="productivity-section">
                <h3>Tasks</h3>
                <form className="productivity-form" onSubmit={createTaskHandler}>
                  <input value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} placeholder="Add a task" required maxLength="200" />
                  <button type="submit">Add task</button>
                </form>
                <ul className="productivity-list task-list">
                  {tasks.map((task) => (
                    <li key={task.id} className={task.status === "completed" ? "completed" : ""}>
                      <span>{task.title}</span>
                      <button type="button" onClick={() => completeTask(task)}>
                        {task.status === "completed" ? "Reopen" : "Complete"}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="productivity-section">
                <h3>Reminders</h3>
                {notificationPermission !== "granted" && (
                  <button
                    type="button"
                    className="notification-button"
                    onClick={enableReminderNotifications}
                    disabled={notificationPermission === "denied" || notificationPermission === "unsupported"}
                  >
                    {notificationPermission === "unsupported"
                      ? "Desktop alerts unavailable"
                      : notificationPermission === "denied"
                        ? "Enable alerts in system settings"
                        : "Enable desktop alerts"}
                  </button>
                )}
                <form className="productivity-form" onSubmit={createReminderHandler}>
                  <input value={reminderTitle} onChange={(event) => setReminderTitle(event.target.value)} placeholder="Reminder" required maxLength="200" />
                  <input type="datetime-local" value={reminderTime} onChange={(event) => setReminderTime(event.target.value)} required />
                  <button type="submit">Set reminder</button>
                </form>
                {dueReminders.length > 0 && (
                  <div className="due-reminders" role="status">
                    <strong>Due now</strong>
                    {dueReminders.map((reminder) => (
                      <div key={reminder.id} className="due-reminder">
                        <span>{reminder.title}</span>
                        <button type="button" onClick={() => acknowledgeReminder(reminder.id, "acknowledge")}>Done</button>
                        <button type="button" onClick={() => acknowledgeReminder(reminder.id, "dismiss")}>Dismiss</button>
                      </div>
                    ))}
                  </div>
                )}
                <ul className="productivity-list">
                  {reminders.filter((reminder) => reminder.status === "pending").map((reminder) => (
                    <li key={reminder.id}><strong>{reminder.title}</strong><p>{new Date(reminder.remind_at).toLocaleString()}</p></li>
                  ))}
                </ul>
              </section>
            </div>
            {productivityError && <p className="engine-error productivity-error" role="alert">{productivityError}</p>}
          </section>

          <section className="online-panel">
            <div className="panel-header memory-header">
              <div>
                <p className="eyebrow">OPT-IN INTERNET</p>
                <h2>Web and service lookups</h2>
              </div>
            </div>
            <div className="online-grid">
              <section className="online-section">
                <h3>Web search</h3>
                <form className="productivity-form" onSubmit={searchWeb}>
                  <input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Search the web" required maxLength="200" />
                  <button type="submit">Search</button>
                </form>
                <ul className="productivity-list">
                  {searchResults.map((result) => (
                    <li key={result.url}>
                      <a href={result.url} target="_blank" rel="noreferrer">{result.title}</a>
                    </li>
                  ))}
                </ul>
              </section>
              <section className="online-section">
                <h3>Weather</h3>
                <form className="productivity-form" onSubmit={lookupWeather}>
                  <input value={weatherLocation} onChange={(event) => setWeatherLocation(event.target.value)} placeholder="City or town" required maxLength="100" />
                  <button type="submit">Get weather</button>
                </form>
                {weatherResult && (
                  <p className="online-result">
                    {weatherResult.location.name}: {weatherResult.current.temperature_2m} {weatherResult.current_units?.temperature_2m || "°C"}, feels like {weatherResult.current.apparent_temperature} {weatherResult.current_units?.temperature_2m || "°C"}; wind {weatherResult.current.wind_speed_10m} {weatherResult.current_units?.wind_speed_10m || "km/h"}.
                  </p>
                )}
              </section>
              <section className="online-section">
                <h3>Public GitHub repository</h3>
                <form className="productivity-form" onSubmit={lookupGithub}>
                  <input value={githubRepository} onChange={(event) => setGithubRepository(event.target.value)} placeholder="owner/repository" required />
                  <button type="submit">Look up</button>
                </form>
                {githubResult && (
                  <p className="online-result">
                    <a href={githubResult.url} target="_blank" rel="noreferrer">{githubResult.name}</a>
                    {` · ${githubResult.language || "Unknown language"} · ${githubResult.stars} stars`}
                  </p>
                )}
              </section>
            </div>
            {onlineError && <p className="engine-error productivity-error" role="alert">{onlineError}</p>}
            <p className="voice-note online-note">These requests send the entered query or location to the selected external service. Chat remains local unless you use these controls.</p>
          </section>

          <footer className="dashboard-footer">
            JARVIS AI DESKTOP ASSISTANT <span>·</span> VERSION 1.0.0
          </footer>
        </section>
      </main>
    </div>
  );
}

export default App;
