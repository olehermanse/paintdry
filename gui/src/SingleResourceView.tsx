import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import type {} from "@mui/x-data-grid/themeAugmentation";
import { Button } from "@mui/material";

interface Resource {
  first_seen: string | null;
  last_seen: string | null;
  modules: string[];
  resource: string;
  id: number | string | null;
  source: string | null;
}

async function fetch_table_data(id: string) {
  const response = await fetch("/api/resources/" + id);
  const resource: Resource = await response.json();
  return resource;
}

function SingleResourceView() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [rawData, setRawData] = useState({});
  const [resource, setResource] = useState("");
  useEffect(() => {
    if (id === undefined) {
      return;
    }
    fetch_table_data(id).then((data) => {
      setRawData(data);
      setResource(data.resource);
    });
  }, [id]);
  return (
    <>
      <h1>
        Resource: {resource} ({id})
      </h1>
      <pre className="code-block">
        <code>{JSON.stringify(rawData, null, 2)}</code>
      </pre>
      <Button
        fullWidth
        variant="outlined"
        onClick={() => {
          navigate("..", { relative: "path" });
        }}
      >
        Back
      </Button>
    </>
  );
}

export default SingleResourceView;
