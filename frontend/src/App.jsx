import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const SCAN_DIRECTORY = "demo_data/demo_drive";
const COMPRESSED_DIRECTORY = "demo_data/demo_drive/compressed";
const QUARANTINE_DIRECTORY = "demo_data/demo_drive/quarantine";
const RESTORE_DIRECTORY = "demo_data/demo_drive/restored";

function App() {
  const [files, setFiles] = useState([]);
  const [duplicateGroups, setDuplicateGroups] = useState([]);
  const [quarantinedFiles, setQuarantinedFiles] = useState([]);

  const [scanning, setScanning] = useState(false);
  const [scanningQuarantine, setScanningQuarantine] = useState(false);

  const [compressingFile, setCompressingFile] = useState("");
  const [quarantiningFile, setQuarantiningFile] = useState("");
  const [restoringFile, setRestoringFile] = useState("");
  const [verifyingFile, setVerifyingFile] = useState("");

  const [verificationHashes, setVerificationHashes] = useState({});
  const [verificationResults, setVerificationResults] = useState({});

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [missionGoal, setMissionGoal] = useState(
    "Recover storage safely"
  );

  const [missionTarget, setMissionTarget] = useState("1");
  const [mission, setMission] = useState(null);
  const [startingMission, setStartingMission] = useState(false);
  const [loadingMission, setLoadingMission] = useState(false);
  const [approvingMission, setApprovingMission] = useState(false);

  // ---------------------------------------------------------
  // SCAN
  // ---------------------------------------------------------

  const scanDirectory = async () => {
    setScanning(true);
    setError("");
    setMessage("");

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

      setFiles(scanData.files);
      setDuplicateGroups(duplicateData.duplicates);
    } catch (err) {
      setError(err.message);
    } finally {
      setScanning(false);
    }
  };

  // ---------------------------------------------------------
  // QUARANTINE SCAN
  // ---------------------------------------------------------

  const scanQuarantine = async () => {
    setScanningQuarantine(true);
    setError("");

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

      setQuarantinedFiles(data.files);

      if (data.files.length === 0) {
        setMessage("No files currently in quarantine.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setScanningQuarantine(false);
    }
  };

  // ---------------------------------------------------------
  // COMPRESS
  // ---------------------------------------------------------

  const compressFile = async (filePath) => {
    setCompressingFile(filePath);
    setError("");
    setMessage("");

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

      await scanDirectory();
    } catch (err) {
      setError(err.message);
    } finally {
      setCompressingFile("");
    }
  };

  // ---------------------------------------------------------
  // QUARANTINE
  // ---------------------------------------------------------

  const quarantineFile = async (filePath) => {
    setQuarantiningFile(filePath);
    setError("");
    setMessage("");

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

      await scanDirectory();
      await scanQuarantine();
    } catch (err) {
      setError(err.message);
    } finally {
      setQuarantiningFile("");
    }
  };

  // ---------------------------------------------------------
  // RESTORE
  // ---------------------------------------------------------

  const restoreFile = async (filePath) => {
    setRestoringFile(filePath);
    setError("");
    setMessage("");

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

      await scanQuarantine();
      await scanDirectory();
    } catch (err) {
      setError(err.message);
    } finally {
      setRestoringFile("");
    }
  };

  // ---------------------------------------------------------
  // VERIFY
  // ---------------------------------------------------------

  const verifyFile = async (filePath) => {
    const expectedHash = verificationHashes[filePath];

    if (!expectedHash || expectedHash.trim() === "") {
      setError(
        "Please enter an expected SHA-256 hash first."
      );
      return;
    }

    setVerifyingFile(filePath);
    setError("");
    setMessage("");

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
      } else {
        setMessage(
          "Verification failed. The file hash does not match."
        );
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setVerifyingFile("");
    }
  };

  // ---------------------------------------------------------
  // START MISSION
  // ---------------------------------------------------------

  const startMission = async () => {
    const targetBytes = Number(missionTarget);

    if (!missionGoal.trim()) {
      setError("Please enter a mission goal.");
      return;
    }

    if (!Number.isInteger(targetBytes) || targetBytes <= 0) {
      setError(
        "Target storage bytes must be a positive whole number."
      );
      return;
    }

    setStartingMission(true);
    setError("");
    setMessage("");

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

      await scanDirectory();
      await scanQuarantine();
    } catch (err) {
      setError(err.message);
    } finally {
      setStartingMission(false);
    }
  };

  // ---------------------------------------------------------
  // APPROVE + RESUME MISSION
  // ---------------------------------------------------------

  const approveMission = async () => {
    if (!mission?.mission_id) {
      setError("No mission is available for approval.");
      return;
    }

    setApprovingMission(true);
    setError("");
    setMessage("");

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

      await scanDirectory();
      await scanQuarantine();
    } catch (err) {
      setError(err.message);
    } finally {
      setApprovingMission(false);
    }
  };

  // ---------------------------------------------------------
  // LOAD MISSION
  // ---------------------------------------------------------

  const loadMission = async () => {
    setLoadingMission(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/mission`
      );

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

  // ---------------------------------------------------------
  // STATS
  // ---------------------------------------------------------

  const totalStorageBytes = files.reduce(
    (total, file) => total + file.size_bytes,
    0
  );

  const totalStorageKB = totalStorageBytes / 1024;

  const duplicateFileCount = duplicateGroups.reduce(
    (total, group) => total + group.length,
    0
  );

  const potentialSavingsBytes = duplicateGroups.reduce(
    (total, group) => {
      if (group.length <= 1) {
        return total;
      }

      const fileSize = group[0].size_bytes;

      return total + fileSize * (group.length - 1);
    },
    0
  );

  const potentialSavingsKB =
    potentialSavingsBytes / 1024;

  const displayFiles = files.filter(
    (file) => !file.name.toLowerCase().endsWith(".gz")
  );

  // ---------------------------------------------------------
  // UI
  // ---------------------------------------------------------

  return (
    <div className="app">
      <header className="topbar">
        <div className="logo">Synora</div>

        <button className="settings-button">
          ⚙ Settings
        </button>
      </header>

      <main className="dashboard">

        {/* HERO */}

        <section className="hero">
          <h1>Your files, under control.</h1>

          <p>
            Scan, understand, and optimize your storage with Synora.
          </p>

          <button
            className="scan-button"
            onClick={scanDirectory}
            disabled={scanning}
          >
            {scanning ? "Scanning..." : "Scan Directory"}
          </button>
        </section>

        {/* MESSAGES */}

        {message && (
          <div className="success-message">
            {message}
          </div>
        )}

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {/* STATS */}

        <section className="stats">
          <div className="stat-card">
            <span>Files Found</span>
            <strong>{files.length}</strong>
          </div>

          <div className="stat-card">
            <span>Duplicate Files</span>
            <strong>{duplicateFileCount}</strong>
          </div>

          <div className="stat-card">
            <span>Storage Used</span>
            <strong>
              {totalStorageKB.toFixed(2)} KB
            </strong>
          </div>

          <div className="stat-card">
            <span>Potential Savings</span>
            <strong>
              {potentialSavingsKB.toFixed(2)} KB
            </strong>
          </div>
        </section>

        {/* MISSION */}

        <section className="recent">
          <div className="section-header">
            <div>
              <h2>Storage Optimization Agent</h2>

              <span>
                Let Synora analyze your files and safely recover storage.
              </span>
            </div>
          </div>

          <div className="mission-controls">
            <div>
              <label>Mission Goal</label>

              <input
                type="text"
                value={missionGoal}
                onChange={(event) =>
                  setMissionGoal(event.target.value)
                }
                placeholder="Recover storage safely"
                disabled={
                  startingMission || approvingMission
                }
              />
            </div>

            <div>
              <label>Target Storage (bytes)</label>

              <input
                type="number"
                min="1"
                value={missionTarget}
                onChange={(event) =>
                  setMissionTarget(event.target.value)
                }
                disabled={
                  startingMission || approvingMission
                }
              />
            </div>

            <div className="mission-buttons">
              <button
                className="scan-button"
                onClick={startMission}
                disabled={
                  startingMission ||
                  approvingMission
                }
              >
                {startingMission
                  ? "Running Mission..."
                  : "Start Mission"}
              </button>

              <button
                className="compress-button"
                onClick={loadMission}
                disabled={
                  loadingMission ||
                  approvingMission
                }
              >
                {loadingMission
                  ? "Loading..."
                  : "Refresh Mission"}
              </button>
            </div>
          </div>

          {mission && (
            <div className="mission-result">

              {/* MISSION HEADER */}

              <div className="mission-header">
                <div>
                  <strong>
                    Mission {mission.mission_id}
                  </strong>

                  <span>
                    {mission.user_goal}
                  </span>
                </div>

                <span className="mission-status">
                  {mission.status}
                </span>
              </div>

              {/* APPROVAL PANEL */}

              {mission.status ===
                "WAITING_FOR_APPROVAL" && (
                <div className="mission-approval">
                  <h3>Approval Required</h3>

                  <p>
                    Synora has identified an action that
                    requires your explicit approval before
                    modifying your files.
                  </p>

                  {mission.failed_actions?.length > 0 && (
                    <div className="approval-action">
                      {mission.failed_actions
                        .filter(
                          (action) =>
                            action.status ===
                            "APPROVAL_REQUIRED"
                        )
                        .map((action, index) => (
                          <div
                            className="mission-action"
                            key={`${action.path || action.action_type}-${index}`}
                          >
                            <span>⚠</span>

                            <div>
                              <strong>
                                {action.action_type}
                              </strong>

                              {action.path && (
                                <span>
                                  {action.path}
                                </span>
                              )}

                              {action.error && (
                                <span>
                                  {action.error}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                    </div>
                  )}

                  <button
                    className="scan-button"
                    onClick={approveMission}
                    disabled={approvingMission}
                  >
                    {approvingMission
                      ? "Approving..."
                      : "Approve & Continue"}
                  </button>
                </div>
              )}

              {/* MISSION STATS */}

              <div className="mission-stats">
                <div>
                  <span>Target</span>

                  <strong>
                    {mission.target_storage_bytes} bytes
                  </strong>
                </div>

                <div>
                  <span>Recovered</span>

                  <strong>
                    {mission.recovered_bytes} bytes
                  </strong>
                </div>

                <div>
                  <span>Completed</span>

                  <strong>
                    {mission.completed_actions?.length || 0}
                  </strong>
                </div>

                <div>
                  <span>Failed</span>

                  <strong>
                    {mission.failed_actions?.length || 0}
                  </strong>
                </div>

                <div>
                  <span>Replans</span>

                  <strong>
                    {mission.replanning_count || 0}
                  </strong>
                </div>
              </div>

              {/* COMPLETED ACTIONS */}

              {mission.completed_actions?.length > 0 && (
                <div className="mission-actions">
                  <h3>Completed Actions</h3>

                  {mission.completed_actions.map(
                    (action, index) => (
                      <div
                        className="mission-action"
                        key={`${action.path || action.action_type}-${index}`}
                      >
                        <span>✓</span>

                        <div>
                          <strong>
                            {action.action_type}
                          </strong>

                          {action.path && (
                            <span>
                              {action.path}
                            </span>
                          )}

                          {action.storage_recovered_bytes !==
                            undefined && (
                            <span>
                              Recovered{" "}
                              {
                                action.storage_recovered_bytes
                              }{" "}
                              bytes
                            </span>
                          )}
                        </div>
                      </div>
                    )
                  )}
                </div>
              )}

              {/* FAILED / PENDING ACTIONS */}

              {mission.failed_actions?.length > 0 && (
                <div className="mission-actions">
                  <h3>
                    {mission.status ===
                    "WAITING_FOR_APPROVAL"
                      ? "Pending Actions"
                      : "Failed Actions"}
                  </h3>

                  {mission.failed_actions.map(
                    (action, index) => (
                      <div
                        className="mission-action"
                        key={`${action.path || action.action_type}-${index}`}
                      >
                        <span>
                          {action.status ===
                          "APPROVAL_REQUIRED"
                            ? "⚠"
                            : "✗"}
                        </span>

                        <div>
                          <strong>
                            {action.action_type}
                          </strong>

                          {action.path && (
                            <span>
                              {action.path}
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

              {/* PROTECTED FILES */}

              {mission.protected_paths?.length > 0 && (
                <div className="mission-actions">
                  <h3>Protected Files</h3>

                  {mission.protected_paths.map(
                    (path, index) => (
                      <div
                        className="mission-action"
                        key={`${path}-${index}`}
                      >
                        <span>🔒</span>

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
          )}
        </section>

        {/* RECENT FINDINGS */}

        <section className="recent">
          <h2>Recent Findings</h2>

          {displayFiles.length === 0 ? (
            <div className="empty-state">
              <p>No scans yet.</p>

              <span>
                Scan a directory to discover optimization opportunities.
              </span>
            </div>
          ) : (
            <div className="file-list">
              {displayFiles.map((file, index) => {
                const isCompressing =
                  compressingFile === file.path;

                const isQuarantining =
                  quarantiningFile === file.path;

                const isVerifying =
                  verifyingFile === file.path;

                const verificationResult =
                  verificationResults[file.path];

                return (
                  <div
                    className="file-item"
                    key={`${file.path}-${index}`}
                  >
                    <div>
                      <strong>{file.name}</strong>

                      <span>{file.path}</span>
                    </div>

                    <div className="file-actions">
                      <span>
                        {file.size_bytes} bytes
                      </span>

                      <button
                        className="compress-button"
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
                        className="quarantine-button"
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
                          ? "Quarantining..."
                          : "Quarantine"}
                      </button>
                    </div>

                    <div className="verification-controls">
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
                        className="compress-button"
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
                          ? "Verifying..."
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
                            : "✗ Not verified"}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* QUARANTINE */}

        <section className="recent">
          <div className="section-header">
            <div>
              <h2>Quarantine Manager</h2>

              <span>
                Review files that have been safely isolated.
              </span>
            </div>

            <button
              className="scan-button"
              onClick={scanQuarantine}
              disabled={scanningQuarantine}
            >
              {scanningQuarantine
                ? "Loading..."
                : "Refresh Quarantine"}
            </button>
          </div>

          {quarantinedFiles.length === 0 ? (
            <div className="empty-state">
              <p>No quarantined files.</p>

              <span>
                Files moved to quarantine will appear here.
              </span>
            </div>
          ) : (
            <div className="file-list">
              {quarantinedFiles.map((file, index) => {
                const isRestoring =
                  restoringFile === file.path;

                return (
                  <div
                    className="file-item"
                    key={`${file.path}-${index}`}
                  >
                    <div>
                      <strong>{file.name}</strong>

                      <span>{file.path}</span>
                    </div>

                    <div className="file-actions">
                      <span>
                        {file.size_bytes} bytes
                      </span>

                      <button
                        className="compress-button"
                        onClick={() =>
                          restoreFile(file.path)
                        }
                        disabled={
                          isRestoring ||
                          restoringFile !== ""
                        }
                      >
                        {isRestoring
                          ? "Restoring..."
                          : "Restore"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;