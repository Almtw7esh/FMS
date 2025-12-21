
import React, { useEffect, useState, useRef } from "react";
import { toast } from "@/components/ui/use-toast";
import { useNavigate } from "react-router-dom";
import { FaRegCommentDots, FaWhatsapp, FaTelegramPlane } from "react-icons/fa";

const COLUMN_NAMES = ["NEW", "Pending", "In Progress"];

const REFRESH_INTERVAL = 120; // seconds
const FMSController = () => {

  const API_URL = import.meta.env.VITE_API_URL;
  const [columns, setColumns] = useState({ NEW: [], Pending: [], "In Progress": [] });
  const [loading, setLoading] = useState(false);
  const [uploadingTasks, setUploadingTasks] = useState<{ [caseNumber: string]: boolean }>({});
  const [taskMessages, setTaskMessages] = useState({});
  const [showNotification, setShowNotification] = useState(false);
  const [notificationMsg, setNotificationMsg] = useState("");
  const [timer, setTimer] = useState(REFRESH_INTERVAL);
  const [workers, setWorkers] = useState<string[]>([]);
  const navigate = useNavigate();

  // Fetch workers list from backend
  useEffect(() => {
    fetch("http://localhost:5000/api/workers")
      .then((res) => res.json())
      .then((data) => {
        console.log("Fetched workers:", data);
        setWorkers(data);
      })
      .catch((err) => {
        console.error("Failed to fetch workers", err);
        setWorkers([]);
      });
  }, []);

  // Redirect to login if not authenticated
  useEffect(() => {
    const username = localStorage.getItem("username");
    if (!username) {
      navigate("/");
    }
  }, [navigate]);

  // Ref to track polling attempts
  const pollingRef = useRef(0);
  useEffect(() => {
    setLoading(true);
    const username = localStorage.getItem("username") || "demo";
    const abortController = new window.AbortController();
    const API_URL = import.meta.env.VITE_API_URL;
    const fetchColumns = async () => {
      try {
        const res = await fetch(`${API_URL}/check_new_tasks?username=${username}`, { signal: abortController.signal });
        const data = await res.json();
        setColumns(data.columns || { NEW: [], Pending: [], "In Progress": [] });
        // After columns, fetch messages for these tasks
        const msgRes = await fetch(`${API_URL}/check_task_messages?username=${username}`, { signal: abortController.signal });
        const msgData = await msgRes.json();
        setTaskMessages(msgData.messages || {});
        // Notification logic: show popup if any task has new message
        const newMsgTasks = Object.entries(msgData.messages || {}).filter(([_, v]) => (v as any).has_new_message);
        if (newMsgTasks.length > 0) {
          setNotificationMsg(`You have new messages in ${newMsgTasks.length} task(s)!`);
          setShowNotification(true);
          setTimeout(() => setShowNotification(false), 4000);
        }
        return data.columns;
      } catch (err) {
        console.error("Error fetching columns:", err);
        setColumns({ NEW: [], Pending: [], "In Progress": [] });
        setTaskMessages({});
        return null;
      } finally {
        setLoading(false);
      }
    };

    // Polling logic for login/first load
    const pollForTasks = async () => {
      pollingRef.current = 0;
      setLoading(true);
      let columnsData = await fetchColumns();
      while (
        columnsData &&
        Object.values(columnsData).every((arr) => Array.isArray(arr) && arr.length === 0) &&
        pollingRef.current < 5
      ) {
        await new Promise((res) => setTimeout(res, 2000));
        pollingRef.current++;
        columnsData = await fetchColumns();
      }
      setLoading(false);
    };
    pollForTasks();
    setTimer(REFRESH_INTERVAL);
    const interval = setInterval(() => {
      fetchColumns();
      setTimer(REFRESH_INTERVAL);
    }, REFRESH_INTERVAL * 1000);
    const timerInterval = setInterval(() => {
      setTimer((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => {
      abortController.abort();
      clearInterval(interval);
      clearInterval(timerInterval);
    };
  }, []);

  const handleClick = () => {
    window.open("https://msp.go2field.iq/board/a22c39cb-093c-d83e-7dd1-a8c7a5d0fa7b", "_blank");
  };

  return (
    <div className="min-h-screen w-full bg-black flex flex-col items-center justify-start overflow-x-auto">
      {/* Logout button in top left */}
      <div style={{ position: "fixed", top: 20, left: 32, zIndex: 100 }}>
        <button
          className="bg-red-600 text-white px-4 py-2 rounded shadow-lg text-lg font-bold hover:bg-red-700 transition-colors"
          onClick={() => {
            localStorage.removeItem("username");
            navigate("/");
            window.location.reload(); // Ensures all requests are aborted and state is reset
          }}
        >
          Logout
        </button>
      </div>
      {/* Timer in top right */}
        <div style={{ position: "fixed", top: 20, right: 32, zIndex: 100 }}>
          <div className="bg-gray-900 text-white px-4 py-2 rounded shadow-lg text-lg font-bold">
            {loading ? "Refreshing..." : `Refresh in: ${timer}s`}
          </div>
        </div>
      {/* Notification popup */}
      {showNotification && (
        <div className="fixed top-8 right-8 bg-blue-600 text-white px-6 py-3 rounded shadow-lg z-50 animate-fade-in">
          <span className="font-bold">🔔</span> {notificationMsg}
        </div>
      )}
      {/* Main columns and tasks */}
      <div className="w-full flex flex-col items-center mt-16 px-2">
        <h1 className="text-5xl font-bold text-white mb-10">FMS Controller</h1>
        {loading ? (
          <div className="flex flex-col items-center justify-center mt-12">
            <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-blue-400 mb-4"></div>
            <div className="text-white text-xl">Scraping tasks, please wait...</div>
          </div>
        ) : (
          <>
            {/* Cards for NEW, Pending, In Progress */}
            <div className="flex flex-row gap-8 mt-12 w-full justify-center overflow-x-auto">
              {COLUMN_NAMES.map((colName) => (
                <div key={colName} className="bg-gray-800 rounded-xl shadow-lg p-6 min-w-[320px] max-w-[400px] flex-1">
                  <h3 className="text-2xl font-bold text-white mb-2">{colName}</h3>
                  <div className="text-lg text-blue-300 mb-4">Tasks: {columns[colName]?.length || 0}</div>
                  <div className="space-y-4">
                    {columns[colName]?.length === 0 ? (
                      <div className="text-gray-400">No tasks</div>
                    ) : (
                      columns[colName].map((task, idx) => (
                        <div key={task.CaseNumber + '-' + idx} className="bg-gray-900 rounded-lg p-4 mb-2 flex flex-col justify-between h-full min-h-[220px]">
                          <div className="font-mono text-white text-base mb-1">{task.CaseNumber} - {task.Title}</div>
                          <div className="text-sm text-gray-400 mb-2">{task.FBG}</div>
                          {/* Task meta info */}
                          <div className="text-xs text-gray-400 mb-2">
                            Created by: <span className="text-white">{task.CreatedBy || 's_creatio'}</span> | Assigned: <span className="text-white">{task.AssignedTo || 'msp_fms'}</span> | <span className="text-white">{task.Date || '01 Dec 2025 11:37'}</span>
                          </div>
                          <div className="flex flex-col gap-2 flex-1">
                              {/* Upload file for this task */}
                              <div className="flex items-center gap-2 mb-2">
                                <button
                                  type="button"
                                  title="Upload file to this task"
                                  style={{ background: "none", border: "none", padding: 0, cursor: "pointer" }}
                                  onClick={() => {
                                    document.getElementById(`file-upload-${task.CaseNumber}`)?.click();
                                  }}
                                >
                                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 text-blue-400 hover:text-blue-600">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 16v-8m0 0l-3.5 3.5M12 8l3.5 3.5M4 16.5V19a2 2 0 002 2h12a2 2 0 002-2v-2.5" />
                                  </svg>
                                </button>
                                <input
                                  id={`file-upload-${task.CaseNumber}`}
                                  type="file"
                                  style={{ display: "none" }}
                                  onChange={async (e) => {
                                    const file = e.target.files?.[0];
                                    if (!file) return;
                                    setUploadingTasks((prev) => ({ ...prev, [task.CaseNumber]: true }));
                                    setLoading(true);
                                    const formData = new FormData();
                                    formData.append("file", file);
                                    formData.append("username", localStorage.getItem("username") || "");
                                    formData.append("password", localStorage.getItem("password") || "");
                                    formData.append("task_filter", task.CaseNumber);
                                    let uploadStarted = false;
                                    try {
                                      const res = await fetch(`${API_URL}/playwright_upload`, {
                                        method: "POST",
                                        body: formData
                                      });
                                      const data = await res.json();
                                      if (res.ok && data.success) {
                                        uploadStarted = true;
                                        toast({
                                          title: "Upload started",
                                          description: `Your file is being uploaded. You will be notified when it is complete.`,
                                          variant: "default"
                                        });
                                        // Poll for upload status every 5 seconds
                                        const pollStatus = async () => {
                                          try {
                                            const statusRes = await fetch(`${API_URL}/upload_status?case_number=${task.CaseNumber}`);
                                            const statusData = await statusRes.json();
                                            if (statusRes.ok && statusData.status === "finished") {
                                              setUploadingTasks((prev) => ({ ...prev, [task.CaseNumber]: false }));
                                              toast({
                                                title: "Upload complete",
                                                description: `File uploaded successfully for task ${task.CaseNumber}.`,
                                                variant: "default"
                                              });
                                              return;
                                            } else if (statusRes.ok && statusData.status === "error") {
                                              setUploadingTasks((prev) => ({ ...prev, [task.CaseNumber]: false }));
                                              toast({
                                                title: "Upload failed",
                                                description: statusData.error || "Unknown error during upload.",
                                                variant: "destructive"
                                              });
                                              return;
                                            } else {
                                              setTimeout(pollStatus, 5000);
                                            }
                                          } catch (err) {
                                            setUploadingTasks((prev) => ({ ...prev, [task.CaseNumber]: false }));
                                            toast({
                                              title: "Upload status error",
                                              description: "Could not check upload status. Try again.",
                                              variant: "destructive"
                                            });
                                          }
                                        };
                                        pollStatus();
                                      } else {
                                        toast({
                                          title: "Upload failed",
                                          description: data.error || data.output || "Unknown error.",
                                          variant: "destructive"
                                        });
                                        setUploadingTasks((prev) => ({ ...prev, [task.CaseNumber]: false }));
                                      }
                                    } catch (err) {
                                      toast({
                                        title: "Network error",
                                        description: "Could not reach backend. Try again.",
                                        variant: "destructive"
                                      });
                                      setUploadingTasks((prev) => ({ ...prev, [task.CaseNumber]: false }));
                                    } finally {
                                      setLoading(false);
                                    }
                                  }}
                                />
                                <span className="text-xs text-blue-300">{uploadingTasks[task.CaseNumber] ? 'Uploading ...' : 'Upload'}</span>
                              </div>
                            {/* Show all messages for this task */}
                            {taskMessages[task.CaseNumber]?.messages && taskMessages[task.CaseNumber].messages.length > 0 && (
                              <div className="flex flex-col gap-2 mt-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <button
                                    type="button"
                                    title="View all messages"
                                    style={{ background: "none", border: "none", padding: 0, cursor: "pointer" }}
                                    onClick={() => {
                                      if (task.uuid) {
                                        window.open(`https://msp.go2field.iq/task/${task.uuid}`, "_blank", "noopener,noreferrer");
                                      }
                                    }}
                                  >
                                    <FaRegCommentDots className="text-green-400 animate-bounce" size={22} />
                                  </button>
                                  <span className="text-xs text-green-300">Messages</span>
                                </div>
                                {taskMessages[task.CaseNumber].messages.map((msg, i) => (
                                  <div key={i} className="text-xs text-gray-300 border-b border-gray-700 pb-1 mb-1">
                                    <span className="font-bold text-blue-300">{msg.sender || ''}</span> {msg.message}
                                    <span className="ml-2 text-gray-400">{msg.date}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                            {/* WhatsApp and Telegram icons */}
                            <div className="flex items-center gap-3 mt-2 flex-wrap">
                                                            {/* Choose Worker Dropdown */}
                                                            <div className="mt-2">
                                                              <label className="text-xs text-white mb-1 block">Choose Worker:</label>
                                                              <div className="flex items-center gap-2">
                                                                <select
                                                                  className="bg-gray-700 text-white px-2 py-1 rounded"
                                                                  value={task.selectedWorker || ""}
                                                                  onChange={e => {
                                                                    task.selectedWorker = e.target.value;
                                                                    if (typeof window !== "undefined") window.dispatchEvent(new Event("worker-select"));
                                                                  }}
                                                                >
                                                                  <option value="" disabled>Select worker</option>
                                                                  {workers.map((worker) => (
                                                                    <option key={worker} value={worker}>{worker}</option>
                                                                  ))}
                                                                </select>
                                                                <button
                                                                  className="bg-blue-600 text-white px-2 py-0.5 rounded shadow hover:bg-blue-700 text-[10px] font-bold ml-1"
                                                                  style={{ minWidth: '60px', height: '22px', lineHeight: '1' }}
                                                                  disabled={task.isApplying}
                                                                  onClick={async () => {
                                                                    const workerName = task.selectedWorker;
                                                                    if (!workerName) {
                                                                      toast({
                                                                        title: "Worker not selected",
                                                                        description: "Please select a worker before assigning.",
                                                                        variant: "destructive"
                                                                      });
                                                                      return;
                                                                    }
                                                                    task.isApplying = true;
                                                                    if (typeof window !== "undefined") window.dispatchEvent(new Event("worker-select"));
                                                                    try {
                                                                      const res = await fetch(`${API_URL}/add_technician`, {
                                                                        method: 'POST',
                                                                        headers: { 'Content-Type': 'application/json' },
                                                                        body: JSON.stringify({
                                                                          task_uuid: task.uuid,
                                                                          worker_name: workerName,
                                                                          case_number: task.CaseNumber
                                                                        })
                                                                      });
                                                                      const data = await res.json();
                                                                      if (res.ok && data.success) {
                                                                        toast({
                                                                          title: "Technician assigned",
                                                                          description: `Successfully assigned ${workerName} to task ${task.CaseNumber}`,
                                                                          variant: "default"
                                                                        });
                                                                        // Wait 3s, then reload to get updated tasks
                                                                        setTimeout(() => {
                                                                          window.location.reload();
                                                                        }, 3000);
                                                                      } else {
                                                                        toast({
                                                                          title: "Assignment failed",
                                                                          description: data.error || data.output || "Unknown error.",
                                                                          variant: "destructive"
                                                                        });
                                                                      }
                                                                    } catch (err) {
                                                                      toast({
                                                                        title: "Network error",
                                                                        description: "Could not reach backend. Try again.",
                                                                        variant: "destructive"
                                                                      });
                                                                    } finally {
                                                                      task.isApplying = false;
                                                                      if (typeof window !== "undefined") window.dispatchEvent(new Event("worker-select"));
                                                                    }
                                                                  }}
                                                                >{task.isApplying ? 'Applying...' : 'Assign'}</button>
                                                              </div>
                                                            </div>
                              <a
                                href={`https://wa.me/?text=${encodeURIComponent(`*${task.CaseNumber} - ${task.Title}*\n${task.FBG}`)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 px-2 py-1 rounded bg-fms-whatsapp/10 hover:bg-fms-whatsapp/20"
                                title="دوره صباحي"
                              >
                                <FaWhatsapp className="text-green-500" size={22} />
                                <span className="text-xs text-white">دوره صباحي</span>
                              </a>
                              <a
                                href={`https://wa.me/?text=${encodeURIComponent(`*${task.CaseNumber} - ${task.Title}*\n${task.FBG}`)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 px-2 py-1 rounded bg-fms-whatsapp/10 hover:bg-fms-whatsapp/20"
                                title="دوره مسائي"
                              >
                                <FaWhatsapp className="text-green-500" size={22} />
                                <span className="text-xs text-white">دوره مسائي</span>
                              </a>
                              <a
                                href={`https://wa.me/?text=${encodeURIComponent(`*${task.CaseNumber} - ${task.Title}*\n${task.FBG}`)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 px-2 py-1 rounded bg-fms-whatsapp/10 hover:bg-fms-whatsapp/20"
                                title="زعفرانيه صباحي"
                              >
                                <FaWhatsapp className="text-green-500" size={22} />
                                <span className="text-xs text-white">زعفرانيه صباحي</span>
                              </a>
                              <a
                                href={`https://wa.me/?text=${encodeURIComponent(`*${task.CaseNumber} - ${task.Title}*\n${task.FBG}`)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 px-2 py-1 rounded bg-fms-whatsapp/10 hover:bg-fms-whatsapp/20"
                                title="زعفرانيه مسائي"
                              >
                                <FaWhatsapp className="text-green-500" size={22} />
                                <span className="text-xs text-white">زعفرانيه مسائي</span>
                              </a>
                              <a
                                href={`https://wa.me/?text=${encodeURIComponent(`*${task.CaseNumber} - ${task.Title}*\n${task.FBG}`)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 px-2 py-1 rounded bg-fms-whatsapp/10 hover:bg-fms-whatsapp/20"
                                title="مدائن صباحي"
                              >
                                <FaWhatsapp className="text-green-500" size={22} />
                                <span className="text-xs text-white">مدائن صباحي</span>
                              </a>
                              <a
                                href={`https://wa.me/?text=${encodeURIComponent(`*${task.CaseNumber} - ${task.Title}*\n${task.FBG}`)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 px-2 py-1 rounded bg-fms-whatsapp/10 hover:bg-fms-whatsapp/20"
                                title="مدائن مسائي"
                              >
                                <FaWhatsapp className="text-green-500" size={22} />
                                <span className="text-xs text-white">مدائن مسائي</span>
                              </a>
                              <a
                                href="https://t.me/test1998tm_bot"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 px-2 py-1 rounded bg-blue-900 hover:bg-blue-800"
                                title="Last Mile Telegram"
                              >
                                <FaTelegramPlane className="text-blue-400" size={22} />
                                <span className="text-xs text-white">Last Mile Telegram</span>
                              </a>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
      {/* Footer */}
      <div className="w-full flex justify-center items-center mt-16 mb-4">
        <span className="text-gray-400 text-lg">Created by Marwan_Al-Ameen</span>
      </div>
    </div>
  );

};

export default FMSController;
