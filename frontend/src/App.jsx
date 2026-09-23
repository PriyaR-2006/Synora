import { useMemo, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const SCAN_DIRECTORY = "demo_data/demo_drive";
const COMPRESSED_DIRECTORY = "demo_data/demo_drive/compressed";
const QUARANTINE_DIRECTORY = "demo_data/demo_drive/quarantine";
const RESTORE_DIRECTORY = "demo_data/demo_drive/restored";

function App() {
  // =========================================================
  // NAVIGATION
  // =========================================================

  const [activePage, setActivePage] = useState("dashboard");
  const [showLanding, setShowLanding] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);

  // =========================================================
  // FILE STATE
  // =========================================================

  const [files, setFiles] = useState([]);
  const [duplicateGroups, setDuplicateGroups] = useState([]);
  const [quarantinedFiles, setQuarantinedFiles] = useState([]);

  // =========================================================
  // LOADING STATE
  // =========================================================

  const [scanning, setScanning] = useState(false);
  const [scanningQuarantine, setScanningQuarantine] = useState(false);

  const [compressingFile, setCompressingFile] = useState("");
  const [quarantiningFile, setQuarantiningFile] = useState("");
  const [restoringFile, setRestoringFile] = useState("");
  const [verifyingFile, setVerifyingFile] = useState("");

  // =========================================================
  // VERIFICATION
  // =========================================================

  const [verificationHashes, setVerificationHashes] = useState({});
  const [verificationResults, setVerificationResults] = useState({});

  // =========================================================
  // MESSAGES
  // =========================================================

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [fileActionError, setFileActionError] = useState(null);

  // =========================================================
  // MISSION
  // =========================================================

  const [missionGoal, setMissionGoal] = useState("");
  const [missionTarget, setMissionTarget] = useState("1");
  const [mission, setMission] = useState(null);

  const [startingMission, setStartingMission] = useState(false);
  const [loadingMission, setLoadingMission] = useState(false);
  const [approvingMission, setApprovingMission] = useState(false);

  // =========================================================
  // HISTORY
  // =========================================================

  const [history, setHistory] = useState([]);

  // =========================================================
  // HELPERS
  // =========================================================

  const addHistory = (type, title, description) => {
    setHistory((previous) => [
      {
        id: Date.now(),
        type,
        title,
        description,
        time: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      },
      ...previous,
    ]);
  };

  const clearMessages = () => {
    setMessage("");
    setError("");
  };

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return "0 B";

    const units = ["B", "KB", "MB", "GB", "TB"];
    const index = Math.floor(Math.log(bytes) / Math.log(1024));

    return `${(bytes / Math.pow(1024, index)).toFixed(
      index === 0 ? 0 : 2
    )} ${units[index]}`;
  };

  const navigate = (page) => {
    setActivePage(page);
    setShowLanding(false);
    setSelectedFile(null);
    clearMessages();
  };

  // =========================================================
  // SCAN
  // =========================================================

  const scanDirectory = async () => {
    setScanning(true);
    clearMessages();
    setFileActionError(null);

    try {
      const scanResponse = await fetch(
        `${API_URL}/scan?directory=${encodeURIComponent(
          SCAN_DIRECTORY
        )}`
      );

      if (!scanResponse.ok) {
        throw new Error("Failed to scan directory");
      }

      const scanData = await scanResponse.json();

      const duplicateResponse = await fetch(
        `${API_URL}/duplicates?directory=${encodeURIComponent(
          SCAN_DIRECTORY
        )}`
      );

      if (!duplicateResponse.ok) {
        throw new Error("Failed to find duplicate files");
      }

      const duplicateData = await duplicateResponse.json();

      setFiles(scanData.files || []);
      setDuplicateGroups(duplicateData.duplicates || []);

      setMessage(
        `Workspace scanned successfully. ${
          scanData.files?.length || 0
        } files discovered.`
      );

      addHistory(
        "scan",
        "Workspace scanned",
        `${scanData.files?.length || 0} files analyzed`
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setScanning(false);
    }
  };

  // =========================================================
  // QUARANTINE SCAN
  // =========================================================

  const scanQuarantine = async () => {
    setScanningQuarantine(true);
    clearMessages();

    try {
      const response = await fetch(
        `${API_URL}/scan?directory=${encodeURIComponent(
          QUARANTINE_DIRECTORY
        )}`
      );

      if (!response.ok) {
        throw new Error("Failed to scan quarantine");
      }

      const data = await response.json();

      setQuarantinedFiles(data.files || []);

      if ((data.files || []).length === 0) {
        setMessage("No files are currently in quarantine.");
      } else {
        setMessage(
          `${data.files.length} quarantined file${
            data.files.length === 1 ? "" : "s"
          } found.`
        );
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setScanningQuarantine(false);
    }
  };

  // =========================================================
  // COMPRESS
  // =========================================================

  const compressFile = async (filePath) => {
    setCompressingFile(filePath);
    clearMessages();
    setFileActionError(null);

    try {
      const response = await fetch(
        `${API_URL}/compress?file_path=${encodeURIComponent(
          filePath
        )}&output_directory=${encodeURIComponent(
          COMPRESSED_DIRECTORY
        )}`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to compress file"
        );
      }

      setMessage(
        `Compressed successfully: ${data.compressed_file}`
      );

      addHistory(
        "success",
        "File compressed",
        filePath
      );

      await scanDirectory();
    } catch (err) {
      setFileActionError({
        path: filePath,
        message: err.message,
      });
    } finally {
      setCompressingFile("");
    }
  };

  // =========================================================
  // QUARANTINE
  // =========================================================

  const quarantineFile = async (filePath) => {
    setQuarantiningFile(filePath);
    clearMessages();
    setFileActionError(null);

    try {
      const response = await fetch(
        `${API_URL}/quarantine?file_path=${encodeURIComponent(
          filePath
        )}&quarantine_directory=${encodeURIComponent(
          QUARANTINE_DIRECTORY
        )}`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to quarantine file"
        );
      }

      setMessage(
        `File quarantined successfully: ${data.quarantined_file}`
      );

      addHistory(
        "warning",
        "File quarantined",
        filePath
      );

      await scanDirectory();
      await scanQuarantine();
    } catch (err) {
      setFileActionError({
        path: filePath,
        message: err.message,
      });
    } finally {
      setQuarantiningFile("");
    }
  };

  // =========================================================
  // RESTORE
  // =========================================================

  const restoreFile = async (filePath) => {
    setRestoringFile(filePath);
    clearMessages();

    try {
      const response = await fetch(
        `${API_URL}/restore?quarantined_file=${encodeURIComponent(
          filePath
        )}&restore_directory=${encodeURIComponent(
          RESTORE_DIRECTORY
        )}`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to restore file"
        );
      }

      setMessage(
        `File restored successfully: ${data.restored_file}`
      );

      addHistory(
        "success",
        "File restored",
        filePath
      );

      await scanQuarantine();
      await scanDirectory();
    } catch (err) {
      setError(err.message);
    } finally {
      setRestoringFile("");
    }
  };

  // =========================================================
  // VERIFY
  // =========================================================

  const verifyFile = async (filePath) => {
    const expectedHash = verificationHashes[filePath];

    if (!expectedHash || expectedHash.trim() === "") {
      setFileActionError({
        path: filePath,
        message:
          "Please enter an expected SHA-256 hash first.",
      });
      return;
    }

    setVerifyingFile(filePath);
    clearMessages();
    setFileActionError(null);

    try {
      const response = await fetch(
        `${API_URL}/verify?file_path=${encodeURIComponent(
          filePath
        )}&expected_hash=${encodeURIComponent(
          expectedHash.trim()
        )}`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to verify file"
        );
      }

      setVerificationResults((previousResults) => ({
        ...previousResults,
        [filePath]: data,
      }));

      if (data.verified) {
        setMessage(
          "Verification successful. The file hash matches."
        );

        addHistory(
          "success",
          "File verified",
          filePath
        );
      } else {
        setMessage(
          "Verification failed. The file hash does not match."
        );

        addHistory(
          "error",
          "Verification failed",
          filePath
        );
      }
    } catch (err) {
      setFileActionError({
        path: filePath,
        message: err.message,
      });
    } finally {
      setVerifyingFile("");
    }
  };

  // =========================================================
  // START MISSION
  // =========================================================

  const startMission = async () => {
    const targetBytes = Number(missionTarget);

    if (!missionGoal.trim()) {
      setError("Please enter a mission goal.");
      return;
    }

    if (
      !Number.isInteger(targetBytes) ||
      targetBytes <= 0
    ) {
      setError(
        "Target storage bytes must be a positive whole number."
      );
      return;
    }

    setStartingMission(true);
    clearMessages();

    try {
      const response = await fetch(
        `${API_URL}/mission?user_goal=${encodeURIComponent(
          missionGoal.trim()
        )}&target_storage_bytes=${encodeURIComponent(
          targetBytes
        )}&directory=${encodeURIComponent(
          SCAN_DIRECTORY
        )}&max_cycles=10`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to start mission"
        );
      }

      setMission(data);

      setMessage(
        `Mission ${data.mission_id} finished with status: ${data.status}`
      );

      addHistory(
        "mission",
        "Mission started",
        missionGoal.trim()
      );

      await scanDirectory();
      await scanQuarantine();
    } catch (err) {
      setError(err.message);
    } finally {
      setStartingMission(false);
    }
  };

  // =========================================================
  // APPROVE MISSION
  // =========================================================

  const approveMission = async () => {
    if (!mission?.mission_id) {
      setError("No mission is available for approval.");
      return;
    }

    setApprovingMission(true);
    clearMessages();

    try {
      const response = await fetch(
        `${API_URL}/mission/approve?mission_id=${encodeURIComponent(
          mission.mission_id
        )}&directory=${encodeURIComponent(
          SCAN_DIRECTORY
        )}&max_cycles=10`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to approve mission"
        );
      }

      setMission(data);

      setMessage(
        `Mission resumed. Status: ${data.status}`
      );

      addHistory(
        "mission",
        "Mission approved",
        `Mission ${data.mission_id}`
      );

      await scanDirectory();
      await scanQuarantine();
    } catch (err) {
      setError(err.message);
    } finally {
      setApprovingMission(false);
    }
  };

  // =========================================================
  // LOAD MISSION
  // =========================================================

  const loadMission = async () => {
    setLoadingMission(true);
    clearMessages();

    try {
      const response = await fetch(`${API_URL}/mission`);

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to load mission"
        );
      }

      setMission(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingMission(false);
    }
  };

  // =========================================================
  // STATS
  // =========================================================

  const totalStorageBytes = useMemo(
    () =>
      files.reduce(
        (total, file) =>
          total + (file.size_bytes || 0),
        0
      ),
    [files]
  );

  const duplicateFileCount = useMemo(
    () =>
      duplicateGroups.reduce(
        (total, group) => total + group.length,
        0
      ),
    [duplicateGroups]
  );

  const potentialSavingsBytes = useMemo(
    () =>
      duplicateGroups.reduce((total, group) => {
        if (group.length <= 1) {
          return total;
        }

        const fileSize = group[0]?.size_bytes || 0;

        return (
          total +
          fileSize * (group.length - 1)
        );
      }, 0),
    [duplicateGroups]
  );

  const displayFiles = useMemo(
    () =>
      files.filter(
        (file) =>
          !file.name
            .toLowerCase()
            .endsWith(".gz")
      ),
    [files]
  );

  // =========================================================
  // LANDING PAGE
  // =========================================================

  if (showLanding) {
    return (
      <div className="landing-page">
        <header className="landing-nav">
          <div className="brand">
            <div className="brand-mark">S</div>

            <div className="brand-copy">
              <div className="logo">Synora</div>

              <span className="brand-subtitle">
                Autonomous digital steward
              </span>
            </div>
          </div>

          <button
            className="landing-login-button"
            onClick={() => {
              setShowLanding(false);
              setActivePage("dashboard");
            }}
          >
            Open workspace
          </button>
        </header>

        <main className="landing-content">
          <section className="landing-hero">
            <div className="landing-hero-copy">
              <span className="eyebrow">
                AUTONOMOUS DIGITAL STEWARD
              </span>

              <h1>
                Your workspace,
                <br />
                intelligently managed.
              </h1>

              <p>
                Synora understands your files, identifies
                optimization opportunities, plans safe actions,
                and verifies the results.
              </p>

              <div className="landing-actions">
                <button
                  className="primary-button large-button"
                  onClick={() => {
                    setShowLanding(false);
                    setActivePage("dashboard");
                  }}
                >
                  Get started
                  <span>→</span>
                </button>

                <button
                  className="text-button"
                  onClick={() => {
                    setShowLanding(false);
                    setActivePage("actions");
                  }}
                >
                  Explore actions
                </button>
              </div>
            </div>

            <div className="landing-visual">
              <div className="visual-window">
                <div className="window-top">
                  <div className="window-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>

                  <span>synora / dashboard</span>
                </div>

                <div className="visual-body">
                  <span className="visual-label">
                    ACTIVE MISSION
                  </span>

                  <strong>
                    Free 10 GB safely
                  </strong>

                  <div className="visual-progress">
                    <span></span>
                  </div>

                  <div className="visual-meta">
                    <span>68% complete</span>
                    <span>3 actions</span>
                  </div>

                  <div className="visual-task">
                    <span className="task-check">
                      ✓
                    </span>

                    <div>
                      <strong>
                        Duplicate analysis
                      </strong>

                      <span>
                        17 groups detected
                      </span>
                    </div>
                  </div>

                  <div className="visual-task">
                    <span className="task-active">
                      •
                    </span>

                    <div>
                      <strong>
                        Compression candidates
                      </strong>

                      <span>
                        Reviewing safe actions
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="landing-workflow">
            <div>
              <span className="eyebrow">
                HOW SYNORA WORKS
              </span>

              <h2>
                From understanding
                <br />
                to verified action.
              </h2>
            </div>

            <div className="landing-steps">
              <div className="landing-step">
                <span>01</span>
                <strong>Understand</strong>
                <p>
                  Analyze your files and workspace context.
                </p>
              </div>

              <div className="landing-step">
                <span>02</span>
                <strong>Plan</strong>
                <p>
                  Determine actions that support your goal.
                </p>
              </div>

              <div className="landing-step">
                <span>03</span>
                <strong>Act</strong>
                <p>
                  Execute supported actions safely.
                </p>
              </div>

              <div className="landing-step">
                <span>04</span>
                <strong>Verify</strong>
                <p>
                  Confirm the result after every action.
                </p>
              </div>
            </div>
          </section>
        </main>
      </div>
    );
  }

  // =========================================================
  // FILE CARD
  // =========================================================

  const renderFileCard = (file, index) => {
    const isCompressing =
      compressingFile === file.path;

    const isQuarantining =
      quarantiningFile === file.path;

    const isVerifying =
      verifyingFile === file.path;

    const verificationResult =
      verificationResults[file.path];

    const isTargetFileError =
      fileActionError &&
      fileActionError.path === file.path;

    return (
      <div
        className={`file-card ${
          selectedFile?.path === file.path
            ? "file-card-selected"
            : ""
        }`}
        key={`${file.path}-${index}`}
      >
        <div
          className="file-card-main"
          onClick={() => setSelectedFile(file)}
        >
          <div className="file-icon">
            {file.name
              .split(".")
              .pop()
              ?.toUpperCase()
              .slice(0, 3)}
          </div>

          <div className="file-information">
            <strong>{file.name}</strong>

            <span>{file.path}</span>
          </div>
        </div>

        <div className="file-card-size">
          {formatBytes(file.size_bytes)}
        </div>

        <div className="file-card-actions">
          <button
            className="small-primary-button"
            onClick={() =>
              compressFile(file.path)
            }
            disabled={
              isCompressing ||
              isQuarantining ||
              isVerifying ||
              scanning
            }
          >
            {isCompressing
              ? "Compressing..."
              : "Compress"}
          </button>

          <button
            className="small-secondary-button"
            onClick={() =>
              quarantineFile(file.path)
            }
            disabled={
              isCompressing ||
              isQuarantining ||
              isVerifying ||
              scanning
            }
          >
            {isQuarantining
              ? "Moving..."
              : "Quarantine"}
          </button>
        </div>

        <div className="verification-row">
          <input
            type="text"
            placeholder="Expected SHA-256 hash"
            value={
              verificationHashes[file.path] || ""
            }
            onChange={(event) =>
              setVerificationHashes(
                (previousHashes) => ({
                  ...previousHashes,
                  [file.path]:
                    event.target.value,
                })
              )
            }
          />

          <button
            className="small-secondary-button"
            onClick={() =>
              verifyFile(file.path)
            }
            disabled={
              isVerifying ||
              isCompressing ||
              isQuarantining ||
              scanning
            }
          >
            {isVerifying
              ? "Checking..."
              : "Verify"}
          </button>

          {verificationResult && (
            <span
              className={
                verificationResult.verified
                  ? "verification-success"
                  : "verification-failure"
              }
            >
              {verificationResult.verified
                ? "✓ Verified"
                : "× Not verified"}
            </span>
          )}
        </div>

        {isTargetFileError && (
          <div className="file-action-error">
            <span className="error-symbol">
              !
            </span>

            <div>
              <strong>Action couldn't be completed</strong>

              <span>
                {fileActionError.message}
              </span>
            </div>
          </div>
        )}
      </div>
    );
  };

  // =========================================================
  // SIDEBAR
  // =========================================================

  const navigationItems = [
    {
      id: "dashboard",
      label: "Dashboard",
      icon: "⌂",
    },
    {
      id: "workspace",
      label: "Workspace",
      icon: "□",
    },
    {
      id: "missions",
      label: "Missions",
      icon: "◎",
    },
    {
      id: "actions",
      label: "Actions",
      icon: "⚡",
    },
    {
      id: "history",
      label: "History",
      icon: "◷",
    },
  ];

  // =========================================================
  // MAIN APPLICATION
  // =========================================================

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark">
            S
          </div>

          <div>
            <strong>Synora</strong>
            <span>Digital steward</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <span className="nav-label">
            WORKSPACE
          </span>

          {navigationItems.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${
                activePage === item.id
                  ? "nav-item-active"
                  : ""
              }`}
              onClick={() =>
                navigate(item.id)
              }
            >
              <span className="nav-icon">
                {item.icon}
              </span>

              <span>{item.label}</span>

              {item.id === "missions" &&
                mission && (
                  <span className="nav-badge">
                    1
                  </span>
                )}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <span className="nav-label">
            SYSTEM
          </span>

          <button
            className={`nav-item ${
              activePage === "settings"
                ? "nav-item-active"
                : ""
            }`}
            onClick={() =>
              navigate("settings")
            }
          >
            <span className="nav-icon">
              ⚙
            </span>

            <span>Settings</span>
          </button>

          <div className="connection-status">
            <span className="connection-dot"></span>

            <div>
              <strong>Backend connected</strong>
              <span>127.0.0.1:8000</span>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="app-header">
          <div>
            <span className="header-context">
              {activePage === "dashboard"
                ? "Overview"
                : activePage === "workspace"
                ? "Workspace"
                : activePage === "missions"
                ? "Mission control"
                : activePage === "actions"
                ? "Action center"
                : activePage === "history"
                ? "Activity"
                : "Configuration"}
            </span>

            <h1>
              {activePage === "dashboard"
                ? "Dashboard"
                : activePage === "workspace"
                ? "Workspace"
                : activePage === "missions"
                ? "Missions"
                : activePage === "actions"
                ? "Actions"
                : activePage === "history"
                ? "History"
                : "Settings"}
            </h1>
          </div>

          <div className="header-right">
            <div className="system-pill">
              <span></span>
              System ready
            </div>

            <div className="avatar">
              S
            </div>
          </div>
        </header>

        {message && (
          <div className="global-message success">
            <span>✓</span>
            {message}
          </div>
        )}

        {error && (
          <div className="global-message error">
            <span>!</span>
            {error}
          </div>
        )}

        <div className="page-content">

          {/* =====================================================
              DASHBOARD
          ===================================================== */}

          {activePage === "dashboard" && (
            <>
              <section className="dashboard-welcome">
                <div>
                  <span className="eyebrow">
                    AUTONOMOUS DIGITAL STEWARD
                  </span>

                  <h2>
                    Your workspace,
                    <br />
                    under control.
                  </h2>

                  <p>
                    Synora understands your files,
                    identifies safe optimization
                    opportunities, and acts toward
                    your goal.
                  </p>

                  <button
                    className="primary-button"
                    onClick={scanDirectory}
                    disabled={scanning}
                  >
                    {scanning
                      ? "Scanning workspace..."
                      : "Scan workspace"}

                    <span>→</span>
                  </button>
                </div>

                <div className="dashboard-status-card">
                  <span className="card-label">
                    WORKSPACE STATUS
                  </span>

                  <div className="status-heading">
                    <span className="large-status-dot"></span>

                    {scanning
                      ? "Analyzing workspace"
                      : files.length > 0
                      ? "Workspace analyzed"
                      : "Ready to analyze"}
                  </div>

                  <p>
                    Scanning is read-only. Synora
                    will inspect your workspace before
                    taking any action.
                  </p>

                  <div className="status-line">
                    <span>Files discovered</span>
                    <strong>{files.length}</strong>
                  </div>

                  <div className="status-line">
                    <span>Potential recovery</span>
                    <strong>
                      {formatBytes(
                        potentialSavingsBytes
                      )}
                    </strong>
                  </div>
                </div>
              </section>

              <section className="stats-grid">
                <div className="dashboard-stat">
                  <span>FILES FOUND</span>
                  <strong>{files.length}</strong>
                  <small>
                    Across scanned workspace
                  </small>
                </div>

                <div className="dashboard-stat">
                  <span>STORAGE USED</span>
                  <strong>
                    {formatBytes(
                      totalStorageBytes
                    )}
                  </strong>
                  <small>
                    Current workspace footprint
                  </small>
                </div>

                <div className="dashboard-stat highlight">
                  <span>POTENTIAL RECOVERY</span>
                  <strong>
                    {formatBytes(
                      potentialSavingsBytes
                    )}
                  </strong>
                  <small>
                    From detected duplicates
                  </small>
                </div>

                <div className="dashboard-stat">
                  <span>DUPLICATES</span>
                  <strong>
                    {duplicateFileCount}
                  </strong>
                  <small>
                    Optimization candidates
                  </small>
                </div>
              </section>

              <section className="dashboard-grid">
                <div className="content-card">
                  <div className="card-heading">
                    <div>
                      <span className="eyebrow">
                        MISSION
                      </span>

                      <h3>
                        {mission
                          ? mission.user_goal
                          : "Storage optimization"}
                      </h3>
                    </div>

                    {mission && (
                      <span className="status-badge">
                        {mission.status}
                      </span>
                    )}
                  </div>

                  {mission ? (
                    <>
                      <div className="mission-progress">
                        <div>
                          <span>
                            Mission progress
                          </span>

                          <strong>
                            {mission.completed_actions
                              ?.length || 0}{" "}
                            actions
                          </strong>
                        </div>

                        <div className="progress-track">
                          <span
                            style={{
                              width: `${
                                Math.min(
                                  100,
                                  ((mission.completed_actions
                                    ?.length ||
                                    0) /
                                    Math.max(
                                      1,
                                      (mission
                                        .completed_actions
                                        ?.length ||
                                        0) +
                                        (mission
                                          .failed_actions
                                          ?.length ||
                                          0) +
                                        1
                                    )) *
                                  100
                                )
                              }%`,
                            }}
                          ></span>
                        </div>
                      </div>

                      <button
                        className="outline-button"
                        onClick={() =>
                          navigate("missions")
                        }
                      >
                        View mission
                      </button>
                    </>
                  ) : (
                    <>
                      <p className="card-description">
                        Give Synora a goal and let the
                        agent determine how to work
                        toward it.
                      </p>

                      <button
                        className="outline-button"
                        onClick={() =>
                          navigate("missions")
                        }
                      >
                        Create a mission
                      </button>
                    </>
                  )}
                </div>

                <div className="content-card">
                  <div className="card-heading">
                    <div>
                      <span className="eyebrow">
                        ACTIVITY
                      </span>

                      <h3>Recent activity</h3>
                    </div>
                  </div>

                  {history.length === 0 ? (
                    <div className="mini-empty">
                      <span>○</span>
                      <p>
                        No activity yet. Run a scan
                        to get started.
                      </p>
                    </div>
                  ) : (
                    <div className="activity-list">
                      {history
                        .slice(0, 4)
                        .map((item) => (
                          <div
                            className="activity-item"
                            key={item.id}
                          >
                            <span
                              className={`activity-dot ${item.type}`}
                            ></span>

                            <div>
                              <strong>
                                {item.title}
                              </strong>

                              <span>
                                {item.description}
                              </span>
                            </div>

                            <time>
                              {item.time}
                            </time>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </section>

              <section className="workflow-card">
                <div>
                  <span className="eyebrow">
                    HOW SYNORA WORKS
                  </span>

                  <h3>
                    From understanding to
                    verified action.
                  </h3>
                </div>

                <div className="workflow-grid">
                  {[
                    [
                      "01",
                      "Understand",
                      "Analyze files and workspace context.",
                    ],
                    [
                      "02",
                      "Plan",
                      "Identify actions that support your goal.",
                    ],
                    [
                      "03",
                      "Act",
                      "Execute supported actions safely.",
                    ],
                    [
                      "04",
                      "Verify",
                      "Confirm the result after every action.",
                    ],
                  ].map(
                    ([number, title, description]) => (
                      <div
                        className="workflow-item"
                        key={number}
                      >
                        <span>{number}</span>

                        <strong>{title}</strong>

                        <p>{description}</p>
                      </div>
                    )
                  )}
                </div>
              </section>
            </>
          )}

          {/* =====================================================
              WORKSPACE
          ===================================================== */}

          {activePage === "workspace" && (
            <section>
              <div className="page-intro">
                <div>
                  <span className="eyebrow">
                    FILE MANAGEMENT
                  </span>

                  <h2>
                    Understand your workspace.
                  </h2>

                  <p>
                    Inspect files, review optimization
                    opportunities, and take controlled
                    actions.
                  </p>
                </div>

                <button
                  className="primary-button"
                  onClick={scanDirectory}
                  disabled={scanning}
                >
                  {scanning
                    ? "Scanning..."
                    : "Scan workspace"}
                </button>
              </div>

              <div className="workspace-summary">
                <div>
                  <span>Files</span>
                  <strong>{files.length}</strong>
                </div>

                <div>
                  <span>Storage</span>
                  <strong>
                    {formatBytes(
                      totalStorageBytes
                    )}
                  </strong>
                </div>

                <div>
                  <span>Duplicates</span>
                  <strong>
                    {duplicateFileCount}
                  </strong>
                </div>

                <div>
                  <span>Recovery</span>
                  <strong>
                    {formatBytes(
                      potentialSavingsBytes
                    )}
                  </strong>
                </div>
              </div>

              <div className="workspace-card">
                <div className="workspace-toolbar">
                  <div>
                    <strong>
                      Workspace files
                    </strong>

                    <span>
                      {displayFiles.length} visible
                      files
                    </span>
                  </div>

                  <div className="toolbar-actions">
                    <button
                      className="toolbar-button"
                      onClick={() =>
                        navigate("actions")
                      }
                    >
                      Actions
                    </button>
                  </div>
                </div>

                {displayFiles.length === 0 ? (
                  <div className="large-empty">
                    <div className="empty-illustration">
                      □
                    </div>

                    <h3>
                      No workspace scan yet
                    </h3>

                    <p>
                      Scan your workspace to
                      discover files and
                      optimization opportunities.
                    </p>

                    <button
                      className="primary-button"
                      onClick={scanDirectory}
                      disabled={scanning}
                    >
                      {scanning
                        ? "Scanning..."
                        : "Scan workspace"}
                    </button>
                  </div>
                ) : (
                  <div className="file-table">
                    <div className="file-table-header">
                      <span>FILE</span>
                      <span>SIZE</span>
                      <span>ACTIONS</span>
                    </div>

                    {displayFiles.map(
                      (file, index) =>
                        renderFileCard(
                          file,
                          index
                        )
                    )}
                  </div>
                )}
              </div>

              {selectedFile && (
                <div className="file-detail-panel">
                  <div className="detail-header">
                    <div>
                      <span className="eyebrow">
                        FILE DETAILS
                      </span>

                      <h3>
                        {selectedFile.name}
                      </h3>
                    </div>

                    <button
                      className="close-button"
                      onClick={() =>
                        setSelectedFile(null)
                      }
                    >
                      ×
                    </button>
                  </div>

                  <div className="detail-grid">
                    <div>
                      <span>Path</span>
                      <strong>
                        {selectedFile.path}
                      </strong>
                    </div>

                    <div>
                      <span>Size</span>
                      <strong>
                        {formatBytes(
                          selectedFile.size_bytes
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>File type</span>
                      <strong>
                        {selectedFile.name
                          .split(".")
                          .pop()
                          ?.toUpperCase() ||
                          "FILE"}
                      </strong>
                    </div>

                    <div>
                      <span>Risk</span>
                      <strong className="safe-text">
                        Review before action
                      </strong>
                    </div>
                  </div>

                  <div className="detail-actions">
                    <button
                      className="primary-button"
                      onClick={() =>
                        compressFile(
                          selectedFile.path
                        )
                      }
                    >
                      Compress
                    </button>

                    <button
                      className="outline-button"
                      onClick={() =>
                        quarantineFile(
                          selectedFile.path
                        )
                      }
                    >
                      Quarantine
                    </button>
                  </div>
                </div>
              )}
            </section>
          )}

          {/* =====================================================
              MISSIONS
          ===================================================== */}

          {activePage === "missions" && (
            <section>
              <div className="page-intro">
                <div>
                  <span className="eyebrow">
                    AGENT CONTROL
                  </span>

                  <h2>
                    Give Synora a goal.
                  </h2>

                  <p>
                    Synora can plan, execute, replan,
                    and verify actions toward your
                    objective.
                  </p>
                </div>
              </div>

              <div className="mission-create-card">
                <div>
                  <span className="card-label">
                    NEW MISSION
                  </span>

                  <h3>
                    What do you want Synora to
                    accomplish?
                  </h3>

                  <p>
                    Describe the goal in natural
                    language.
                  </p>
                </div>

                <div className="mission-form">
                  <div className="form-field large">
                    <label>Mission goal</label>

                    <input
                      type="text"
                      value={missionGoal}
                      onChange={(event) =>
                        setMissionGoal(
                          event.target.value
                        )
                      }
                      placeholder="Recover storage safely without affecting active projects"
                      disabled={
                        startingMission ||
                        approvingMission
                      }
                    />
                  </div>

                  <div className="form-field">
                    <label>
                      Target storage (bytes)
                    </label>

                    <input
                      type="number"
                      min="1"
                      value={missionTarget}
                      onChange={(event) =>
                        setMissionTarget(
                          event.target.value
                        )
                      }
                      disabled={
                        startingMission ||
                        approvingMission
                      }
                    />
                  </div>

                  <button
                    className="primary-button"
                    onClick={startMission}
                    disabled={
                      startingMission ||
                      approvingMission
                    }
                  >
                    {startingMission
                      ? "Running mission..."
                      : "Start mission"}
                  </button>

                  <button
                    className="outline-button"
                    onClick={loadMission}
                    disabled={
                      loadingMission ||
                      approvingMission
                    }
                  >
                    {loadingMission
                      ? "Loading..."
                      : "Load mission"}
                  </button>
                </div>
              </div>

              {mission ? (
                <div className="mission-detail-card">
                  <div className="mission-detail-header">
                    <div>
                      <span className="eyebrow">
                        CURRENT MISSION
                      </span>

                      <h3>
                        {mission.user_goal}
                      </h3>

                      <p>
                        Mission ID:{" "}
                        {mission.mission_id}
                      </p>
                    </div>

                    <span className="status-badge">
                      {mission.status}
                    </span>
                  </div>

                  <div className="mission-overview">
                    <div>
                      <span>Target</span>
                      <strong>
                        {formatBytes(
                          mission.target_storage_bytes
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>Recovered</span>
                      <strong>
                        {formatBytes(
                          mission.recovered_bytes
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>Completed</span>
                      <strong>
                        {mission
                          .completed_actions
                          ?.length || 0}
                      </strong>
                    </div>

                    <div>
                      <span>Failed</span>
                      <strong>
                        {mission
                          .failed_actions
                          ?.length || 0}
                      </strong>
                    </div>

                    <div>
                      <span>Replans</span>
                      <strong>
                        {mission.replanning_count ||
                          0}
                      </strong>
                    </div>
                  </div>

                  {mission.status ===
                    "WAITING_FOR_APPROVAL" && (
                    <div className="approval-panel">
                      <div className="approval-icon">
                        !
                      </div>

                      <div>
                        <span className="eyebrow">
                          HUMAN APPROVAL
                        </span>

                        <h3>
                          Review required
                        </h3>

                        <p>
                          Synora identified an
                          action that requires
                          explicit approval before
                          modifying files.
                        </p>

                        {mission.failed_actions
                          ?.filter(
                            (action) =>
                              action.status ===
                              "APPROVAL_REQUIRED"
                          )
                          .map(
                            (
                              action,
                              index
                            ) => (
                              <div
                                className="approval-item"
                                key={`${action.path}-${index}`}
                              >
                                <strong>
                                  {
                                    action.action_type
                                  }
                                </strong>

                                {action.path && (
                                  <span>
                                    {
                                      action.path
                                    }
                                  </span>
                                )}

                                {action.error && (
                                  <span>
                                    {
                                      action.error
                                    }
                                  </span>
                                )}
                              </div>
                            )
                          )}

                        <button
                          className="primary-button"
                          onClick={
                            approveMission
                          }
                          disabled={
                            approvingMission
                          }
                        >
                          {approvingMission
                            ? "Approving..."
                            : "Approve & continue"}
                        </button>
                      </div>
                    </div>
                  )}

                  {mission.completed_actions
                    ?.length > 0 && (
                    <div className="mission-section-block">
                      <div className="block-heading">
                        <span className="eyebrow">
                          EXECUTION
                        </span>

                        <h3>
                          Completed actions
                        </h3>
                      </div>

                      {mission.completed_actions.map(
                        (action, index) => (
                          <div
                            className="mission-list-item"
                            key={`${action.path}-${index}`}
                          >
                            <span className="list-icon success">
                              ✓
                            </span>

                            <div>
                              <strong>
                                {
                                  action.action_type
                                }
                              </strong>

                              {action.path && (
                                <span>
                                  {
                                    action.path
                                  }
                                </span>
                              )}

                              {action.storage_recovered_bytes !==
                                undefined && (
                                <span>
                                  Recovered{" "}
                                  {formatBytes(
                                    action.storage_recovered_bytes
                                  )}
                                </span>
                              )}
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  )}

                  {mission.failed_actions
                    ?.length > 0 && (
                    <div className="mission-section-block">
                      <div className="block-heading">
                        <span className="eyebrow">
                          REVIEW
                        </span>

                        <h3>
                          {mission.status ===
                          "WAITING_FOR_APPROVAL"
                            ? "Pending actions"
                            : "Failed actions"}
                        </h3>
                      </div>

                      {mission.failed_actions.map(
                        (action, index) => (
                          <div
                            className="mission-list-item"
                            key={`${action.path}-${index}`}
                          >
                            <span className="list-icon warning">
                              {action.status ===
                              "APPROVAL_REQUIRED"
                                ? "!"
                                : "×"}
                            </span>

                            <div>
                              <strong>
                                {
                                  action.action_type
                                }
                              </strong>

                              {action.path && (
                                <span>
                                  {
                                    action.path
                                  }
                                </span>
                              )}

                              {action.error && (
                                <span>
                                  {action.error}
                                </span>
                              )}
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  )}

                  {mission.protected_paths
                    ?.length > 0 && (
                    <div className="mission-section-block">
                      <div className="block-heading">
                        <span className="eyebrow">
                          SAFETY
                        </span>

                        <h3>
                          Protected files
                        </h3>
                      </div>

                      {mission.protected_paths.map(
                        (path, index) => (
                          <div
                            className="mission-list-item"
                            key={`${path}-${index}`}
                          >
                            <span className="list-icon protected">
                              🔒
                            </span>

                            <div>
                              <strong>
                                Protected
                              </strong>

                              <span>{path}</span>
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="large-empty">
                  <div className="empty-illustration">
                    ◎
                  </div>

                  <h3>
                    No active mission
                  </h3>

                  <p>
                    Create a mission above and
                    Synora will determine how to
                    work toward the goal.
                  </p>
                </div>
              )}
            </section>
          )}

          {/* =====================================================
              ACTIONS
          ===================================================== */}

          {activePage === "actions" && (
            <section>
              <div className="page-intro">
                <div>
                  <span className="eyebrow">
                    ACTION CENTER
                  </span>

                  <h2>
                    Take controlled action.
                  </h2>

                  <p>
                    Run individual workspace operations
                    or let a mission coordinate them.
                  </p>
                </div>
              </div>

              <div className="action-grid">
                <div className="action-card">
                  <div className="action-card-icon">
                    ◌
                  </div>

                  <span className="eyebrow">
                    ANALYZE
                  </span>

                  <h3>
                    Scan workspace
                  </h3>

                  <p>
                    Analyze the workspace and discover
                    files that may need attention.
                  </p>

                  <button
                    className="primary-button"
                    onClick={scanDirectory}
                    disabled={scanning}
                  >
                    {scanning
                      ? "Scanning..."
                      : "Run scan"}
                  </button>
                </div>

                <div className="action-card">
                  <div className="action-card-icon">
                    ◈
                  </div>

                  <span className="eyebrow">
                    DETECT
                  </span>

                  <h3>
                    Find duplicates
                  </h3>

                  <p>
                    Identify duplicate files that may
                    represent storage recovery
                    opportunities.
                  </p>

                  <button
                    className="outline-button"
                    onClick={scanDirectory}
                    disabled={scanning}
                  >
                    {scanning
                      ? "Analyzing..."
                      : "Analyze duplicates"}
                  </button>
                </div>

                <div className="action-card">
                  <div className="action-card-icon">
                    ↓
                  </div>

                  <span className="eyebrow">
                    OPTIMIZE
                  </span>

                  <h3>
                    Compress files
                  </h3>

                  <p>
                    Compress selected files without
                    directly deleting the original
                    workspace file.
                  </p>

                  <button
                    className="outline-button"
                    onClick={() =>
                      navigate("workspace")
                    }
                  >
                    Choose files
                  </button>
                </div>

                <div className="action-card">
                  <div className="action-card-icon warning-icon">
                    !
                  </div>

                  <span className="eyebrow">
                    SAFETY
                  </span>

                  <h3>
                    Quarantine
                  </h3>

                  <p>
                    Safely isolate files for review
                    without permanently deleting them.
                  </p>

                  <button
                    className="outline-button"
                    onClick={() =>
                      navigate("workspace")
                    }
                  >
                    Choose files
                  </button>
                </div>

                <div className="action-card">
                  <div className="action-card-icon">
                    ↩
                  </div>

                  <span className="eyebrow">
                    RECOVERY
                  </span>

                  <h3>
                    Restore files
                  </h3>

                  <p>
                    Review quarantined files and restore
                    them to the configured location.
                  </p>

                  <button
                    className="outline-button"
                    onClick={scanQuarantine}
                    disabled={scanningQuarantine}
                  >
                    {scanningQuarantine
                      ? "Loading..."
                      : "View quarantine"}
                  </button>
                </div>

                <div className="action-card">
                  <div className="action-card-icon">
                    ✓
                  </div>

                  <span className="eyebrow">
                    VERIFY
                  </span>

                  <h3>
                    Verify integrity
                  </h3>

                  <p>
                    Compare a file's SHA-256 hash
                    against an expected value.
                  </p>

                  <button
                    className="outline-button"
                    onClick={() =>
                      navigate("workspace")
                    }
                  >
                    Verify files
                  </button>
                </div>
              </div>

              <div className="quarantine-panel">
                <div className="panel-heading">
                  <div>
                    <span className="eyebrow">
                      SAFETY
                    </span>

                    <h3>
                      Quarantine manager
                    </h3>

                    <p>
                      Files isolated by Synora are
                      listed here for review.
                    </p>
                  </div>

                  <button
                    className="outline-button"
                    onClick={
                      scanQuarantine
                    }
                    disabled={
                      scanningQuarantine
                    }
                  >
                    {scanningQuarantine
                      ? "Refreshing..."
                      : "Refresh"}
                  </button>
                </div>

                {quarantinedFiles.length ===
                0 ? (
                  <div className="mini-empty">
                    <span>✓</span>

                    <div>
                      <strong>
                        No quarantined files
                      </strong>

                      <p>
                        Files moved to quarantine
                        will appear here.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="quarantine-list">
                    {quarantinedFiles.map(
                      (file, index) => {
                        const isRestoring =
                          restoringFile ===
                          file.path;

                        return (
                          <div
                            className="quarantine-item"
                            key={`${file.path}-${index}`}
                          >
                            <div>
                              <strong>
                                {file.name}
                              </strong>

                              <span>
                                {file.path}
                              </span>
                            </div>

                            <div>
                              <span>
                                {formatBytes(
                                  file.size_bytes
                                )}
                              </span>

                              <button
                                className="small-primary-button"
                                onClick={() =>
                                  restoreFile(
                                    file.path
                                  )
                                }
                                disabled={
                                  isRestoring ||
                                  restoringFile !==
                                    ""
                                }
                              >
                                {isRestoring
                                  ? "Restoring..."
                                  : "Restore"}
                              </button>
                            </div>
                          </div>
                        );
                      }
                    )}
                  </div>
                )}
              </div>
            </section>
          )}

          {/* =====================================================
              HISTORY
          ===================================================== */}

          {activePage === "history" && (
            <section>
              <div className="page-intro">
                <div>
                  <span className="eyebrow">
                    ACTIVITY
                  </span>

                  <h2>
                    Everything Synora did.
                  </h2>

                  <p>
                    Review scans, actions, missions,
                    and verification events.
                  </p>
                </div>

                {history.length > 0 && (
                  <button
                    className="outline-button"
                    onClick={() =>
                      setHistory([])
                    }
                  >
                    Clear local history
                  </button>
                )}
              </div>

              <div className="history-card">
                {history.length === 0 ? (
                  <div className="large-empty">
                    <div className="empty-illustration">
                      ◷
                    </div>

                    <h3>
                      No activity yet
                    </h3>

                    <p>
                      Your Synora actions will
                      appear here as you use the
                      application.
                    </p>
                  </div>
                ) : (
                  <div className="history-list">
                    {history.map((item) => (
                      <div
                        className="history-item"
                        key={item.id}
                      >
                        <div
                          className={`history-icon ${item.type}`}
                        >
                          {item.type ===
                          "success"
                            ? "✓"
                            : item.type ===
                              "error"
                            ? "!"
                            : item.type ===
                              "mission"
                            ? "◎"
                            : "◌"}
                        </div>

                        <div className="history-content">
                          <strong>
                            {item.title}
                          </strong>

                          <span>
                            {item.description}
                          </span>
                        </div>

                        <time>
                          {item.time}
                        </time>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>
          )}

          {/* =====================================================
              SETTINGS
          ===================================================== */}

          {activePage === "settings" && (
            <section>
              <div className="page-intro">
                <div>
                  <span className="eyebrow">
                    CONFIGURATION
                  </span>

                  <h2>
                    Synora settings.
                  </h2>

                  <p>
                    Current workspace and system
                    configuration.
                  </p>
                </div>
              </div>

              <div className="settings-grid">
                <div className="settings-card">
                  <span className="eyebrow">
                    WORKSPACE
                  </span>

                  <h3>
                    Workspace configuration
                  </h3>

                  <div className="setting-row">
                    <div>
                      <strong>
                        Scan directory
                      </strong>

                      <span>
                        Directory currently used
                        by Synora.
                      </span>
                    </div>

                    <code>
                      {SCAN_DIRECTORY}
                    </code>
                  </div>

                  <div className="setting-row">
                    <div>
                      <strong>
                        Compressed files
                      </strong>

                      <span>
                        Destination for compressed
                        output.
                      </span>
                    </div>

                    <code>
                      {COMPRESSED_DIRECTORY}
                    </code>
                  </div>
                </div>

                <div className="settings-card">
                  <span className="eyebrow">
                    SAFETY
                  </span>

                  <h3>
                    File protection
                  </h3>

                  <div className="setting-row">
                    <div>
                      <strong>
                        Quarantine
                      </strong>

                      <span>
                        Files can be isolated and
                        restored.
                      </span>
                    </div>

                    <span className="setting-status">
                      Enabled
                    </span>
                  </div>

                  <div className="setting-row">
                    <div>
                      <strong>
                        Verification
                      </strong>

                      <span>
                        SHA-256 integrity checking.
                      </span>
                    </div>

                    <span className="setting-status">
                      Enabled
                    </span>
                  </div>

                  <div className="setting-row">
                    <div>
                      <strong>
                        Mission approval
                      </strong>

                      <span>
                        Actions can require human
                        approval.
                      </span>
                    </div>

                    <span className="setting-status">
                      Enabled
                    </span>
                  </div>
                </div>

                <div className="settings-card">
                  <span className="eyebrow">
                    SYSTEM
                  </span>

                  <h3>
                    Connection
                  </h3>

                  <div className="system-connection">
                    <span></span>

                    <div>
                      <strong>
                        Backend connected
                      </strong>

                      <p>
                        Synora API is available at
                        {` ${API_URL}`}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;