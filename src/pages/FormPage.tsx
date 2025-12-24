import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import "../form-dark.css";

const WhiteBox: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div className="white-box bg-white rounded shadow p-4 mb-4">
    <div className="flex items-center mb-2">
      <h4 className="flex-grow text-lg font-semibold">{title}</h4>
    </div>
    <div>{children}</div>
  </div>
);

// Helper: get the real form template (handles formTemplate stringified JSON)
function extractFormTemplate(data: any) {
  if (data && typeof data.formTemplate === "string") {
    try {
      return JSON.parse(data.formTemplate);
    } catch {
      return null;
    }
  }
  if (data && data.components) return data;
  return null;
}

const FormPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const [formTemplate, setFormTemplate] = useState<any>(null);
  const [formData, setFormData] = useState<any>({});
  const [templateName, setTemplateName] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();

  useEffect(() => {
    const fetchFormTemplate = async () => {
      try {
        let response;
        if (taskId && taskId.endsWith('.json')) {
          response = await fetch(`/api/form-template/${taskId}`);
        } else {
          response = await fetch(`/api/form/${taskId}`);
        }
        if (!response.ok) throw new Error("Failed to fetch form template");
        const data = await response.json();
        setFormTemplate(extractFormTemplate(data));
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchFormTemplate();
  }, [taskId]);

  // Handles all field changes (including nested fields)
  const handleChange = (key: string, value: any) => {
    setFormData((prev: any) => ({ ...prev, [key]: value }));
  };


  const handleSave = async () => {
    try {
      if (!templateName.trim()) {
        alert("Please enter a template name before saving.");
        return;
      }
      const response = await fetch("/api/save-form-template", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ taskId: templateName, formData }),
      });
      if (!response.ok) throw new Error("Failed to save form");
      alert("Form saved successfully!");
    } catch (err: any) {
      alert(err.message);
    }
  };


  if (loading) return <div className="p-8 text-center">Loading...</div>;
  if (error) return <div className="p-8 text-red-500">{error}</div>;

  // Render a single field/component
  const renderField = (field: any) => {
    if (!field || field.type === "button" || field.type === "content") return null;
    switch (field.type) {
      case "select":
        return (
          <div className="form-group mb-4" key={field.key}>
            <label className={`col-form-label${field.required ? " field-required" : ""}`}>{field.label}</label>
            <select
              name={field.key}
              value={formData[field.key] || ""}
              onChange={e => handleChange(field.key, e.target.value)}
              className="form-control choices__input border rounded px-3 py-2 w-full"
              required={field.required}
            >
              <option value="">Select...</option>
              {field.data?.values?.map((opt: any) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
              {field.options?.map((opt: any) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        );
      case "textfield":
        return (
          <div className="form-group mb-4" key={field.key}>
            <label className={`col-form-label${field.required ? " field-required" : ""}`}>{field.label}</label>
            <input
              type="text"
              name={field.key}
              value={formData[field.key] || ""}
              onChange={e => handleChange(field.key, e.target.value)}
              className="form-control border rounded px-3 py-2 w-full"
              required={field.required}
            />
          </div>
        );
      case "number":
        return (
          <div className="form-group mb-4" key={field.key}>
            <label className={`col-form-label${field.required ? " field-required" : ""}`}>{field.label}</label>
            <input
              type="number"
              name={field.key}
              value={formData[field.key] || ""}
              onChange={e => handleChange(field.key, e.target.value)}
              className="form-control border rounded px-3 py-2 w-full"
              required={field.required}
            />
          </div>
        );
      case "checkbox":
        return (
          <div className="form-group mb-4 flex items-center" key={field.key}>
            <input
              type="checkbox"
              name={field.key}
              checked={!!formData[field.key]}
              onChange={e => handleChange(field.key, e.target.checked)}
              className="form-check-input mr-2"
            />
            <label className="form-check-label font-medium">{field.label}</label>
          </div>
        );
      case "selectboxes":
        return (
          <div className="form-group mb-4" key={field.key}>
            <label className="col-form-label font-medium">{field.label}</label>
            <div className="flex flex-wrap gap-4 mt-1">
              {field.values?.map((opt: any) => (
                <label key={opt.value} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={Array.isArray(formData[field.key]) ? formData[field.key].includes(opt.value) : false}
                    onChange={e => {
                      const arr = Array.isArray(formData[field.key]) ? [...formData[field.key]] : [];
                      if (e.target.checked) arr.push(opt.value);
                      else arr.splice(arr.indexOf(opt.value), 1);
                      handleChange(field.key, arr);
                    }}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>
        );
      case "datetime":
        return (
          <div className="form-group mb-4" key={field.key}>
            <label className="col-form-label font-medium">{field.label}</label>
            <input
              type="datetime-local"
              name={field.key}
              value={formData[field.key] || ""}
              onChange={e => handleChange(field.key, e.target.value)}
              className="form-control border rounded px-3 py-2 w-full"
            />
          </div>
        );
      case "location":
        return (
          <div className="form-group mb-4" key={field.key}>
            <label className="col-form-label font-medium">{field.label}</label>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Latitude"
                value={formData[`${field.key}_lat`] || ""}
                onChange={e => handleChange(`${field.key}_lat`, e.target.value)}
                className="form-control border rounded px-3 py-2 w-full"
              />
              <input
                type="text"
                placeholder="Longitude"
                value={formData[`${field.key}_lng`] || ""}
                onChange={e => handleChange(`${field.key}_lng`, e.target.value)}
                className="form-control border rounded px-3 py-2 w-full"
              />
            </div>
          </div>
        );
      case "fmsfile":
        return (
          <div className="form-group mb-4" key={field.key}>
            <label className="col-form-label font-medium">{field.label}</label>
            <input
              type="file"
              name={field.key}
              onChange={e => handleChange(field.key, e.target.files?.[0] || null)}
              className="form-control border rounded px-3 py-2 w-full"
            />
          </div>
        );
      default:
        // For unknown types, fallback to text input
        if (field.components) {
          // Nested structure: render recursively
          return renderSection(field);
        }
        return null;
    }
  };

  // Render a section/fieldset/panel/columns/datagrid recursively
  const renderSection = (section: any) => {
    if (!section) return null;
    if (section.type === "fieldset" || section.type === "panel") {
      return (
        <fieldset key={section.key || section.label} className="mb-6 border rounded p-4">
          <legend className="font-semibold text-base mb-2">{section.legend || section.label}</legend>
          {section.components?.map((field: any) => renderField(field))}
        </fieldset>
      );
    }
    if (section.type === "columns") {
      return (
        <div key={section.key || section.label} className="flex gap-4 mb-4">
          {section.columns?.map((col: any, idx: number) => (
            <div key={idx} className="flex-1">{col.components?.map((field: any) => renderField(field))}</div>
          ))}
        </div>
      );
    }
    if (section.type === "datagrid") {
      // For simplicity, render a single row (extend for full datagrid support)
      return (
        <div key={section.key || section.label} className="mb-4">
          <label className="font-semibold mb-2 block">{section.label}</label>
          {section.components?.map((field: any) => renderField(field))}
        </div>
      );
    }
    // Fallback: render as a group
    if (section.components) {
      return section.components.map((field: any) => renderField(field));
    }
    return null;
  };

  return (
    <div className="min-h-screen bg-black p-2 md:p-6 form-dark-bg">
      <div className="max-w-5xl mx-auto">
        <button
          className="mb-4 text-blue-600 hover:underline"
          onClick={() => navigate(-1)}
        >
          &larr; Back
        </button>
        <WhiteBox title="Task Form">
          <form
            onSubmit={e => {
              e.preventDefault();
              handleSave();
            }}
            className="space-y-4"
          >
            {/* Template Name Input */}
            <div className="mb-4">
              <label htmlFor="templateName" className="block font-semibold mb-2 text-white">Template File Name</label>
              <input
                id="templateName"
                type="text"
                className="form-control border rounded px-3 py-2 w-full bg-[#222] text-white"
                placeholder="Enter template name (e.g. customer_form_1)"
                value={templateName}
                onChange={e => setTemplateName(e.target.value)}
                autoComplete="off"
              />
            </div>
            {formTemplate?.components
              ? formTemplate.components.map((section: any, idx: number) => renderSection(section))
              : <div className="text-gray-400 italic">No fields to display for this form.</div>
            }
            <div className="flex gap-2 mt-6">
              <button
                type="submit"
                className="btn btn-primary px-6 py-2 rounded text-white bg-blue-600 hover:bg-blue-700"
              >
                Save Template
              </button>
            </div>
          </form>
        </WhiteBox>
      </div>
    </div>
  );
};

export default FormPage;