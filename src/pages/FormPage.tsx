import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";



const WhiteBox: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div className="white-box bg-white rounded shadow p-4 mb-4">
    <div className="flex items-center mb-2">
      <h4 className="flex-grow text-lg font-semibold">{title}</h4>
    </div>
    <div>{children}</div>
  </div>
);

const FormPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const [formTemplate, setFormTemplate] = useState<any>(null);
  const [formData, setFormData] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();

  useEffect(() => {
    const fetchFormTemplate = async () => {
      try {
        const response = await fetch(`/api/form/${taskId}`);
        if (!response.ok) throw new Error("Failed to fetch form template");
        const data = await response.json();
        setFormTemplate(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchFormTemplate();
  }, [taskId]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev: any) => {
      if (type === "checkbox") {
        // Handle multiple checkboxes (array) and single checkbox
        if (Array.isArray(prev[name])) {
          // For checkbox groups (e.g., name="data[cableSplice2][]")
          if (checked) {
            return { ...prev, [name]: [...prev[name], value] };
          } else {
            return { ...prev, [name]: prev[name].filter((v: any) => v !== value) };
          }
        } else {
          // For single checkbox
          return { ...prev, [name]: checked };
        }
      } else {
        return { ...prev, [name]: value };
      }
    });
  };

  const handleSave = async () => {
    try {
      const response = await fetch("/api/save-form-template", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ taskId, formData }),
      });
      if (!response.ok) throw new Error("Failed to save form");
      alert("Form saved successfully!");
    } catch (err: any) {
      alert(err.message);
    }
  };

  if (loading) return <div className="p-8 text-center">Loading...</div>;
  if (error) return <div className="p-8 text-red-500">{error}</div>;

  // Helper to render fields (with improved structure)
  const renderField = (field: any) => {
    switch (field.type) {
      case "select":
        return (
          <div className="form-group mb-4" key={field.name}>
            <label className={`col-form-label${field.required ? " field-required" : ""}`}>{field.label}</label>
            <select
              name={field.name}
              value={formData[field.name] || ""}
              onChange={handleChange}
              className="form-control choices__input border rounded px-3 py-2 w-full"
              required={field.required}
            >
              <option value="">Select...</option>
              {field.options?.map((opt: any) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        );
      case "textarea":
        return (
          <div className="form-group mb-4" key={field.name}>
            <label className={`col-form-label${field.required ? " field-required" : ""}`}>{field.label}</label>
            <textarea
              name={field.name}
              value={formData[field.name] || ""}
              onChange={handleChange}
              className="form-control border rounded px-3 py-2 w-full"
              required={field.required}
            />
          </div>
        );
      case "checkbox":
        return (
          <div className="form-group mb-4 flex items-center" key={field.name}>
            <input
              type="checkbox"
              name={field.name}
              checked={!!formData[field.name]}
              onChange={handleChange}
              className="form-check-input mr-2"
            />
            <label className="form-check-label font-medium">{field.label}</label>
          </div>
        );
      default:
        return (
          <div className="form-group mb-4" key={field.name}>
            <label className={`col-form-label${field.required ? " field-required" : ""}`}>{field.label}</label>
            <input
              type={field.type}
              name={field.name}
              value={formData[field.name] || ""}
              onChange={handleChange}
              className="form-control border rounded px-3 py-2 w-full"
              required={field.required}
            />
          </div>
        );
    }
  };

  // Main layout: Only Task Form
  return (
    <div className="min-h-screen bg-black p-2 md:p-6">
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
            {/* Render sections or fields, or show a message if none */}
            {formTemplate?.sections && formTemplate.sections.length > 0 ? (
              formTemplate.sections.map((section: any, idx: number) => (
                <fieldset key={idx} className="mb-6 border rounded p-4">
                  <legend className="font-semibold text-base mb-2">{section.title}</legend>
                  {section.fields.map(renderField)}
                </fieldset>
              ))
            ) : formTemplate?.fields && formTemplate.fields.length > 0 ? (
              formTemplate.fields.map(renderField)
            ) : (
              <div className="text-gray-400 italic">No fields to display for this form.</div>
            )}
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