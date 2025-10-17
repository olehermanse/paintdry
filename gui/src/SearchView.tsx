import { useState } from "react";
import { Box, TextField, Paper, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from "@mui/material";

interface SearchResult {
  type: string;
  resource: string;
  module: string;
  attribute?: string;
  value?: string;
  old_value?: string;
  new_value?: string;
  source?: string;
  first_seen: string;
  last_seen: string;
}

const SearchView = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);

  const handleSearch = async (value: string) => {
    setSearchTerm(value);

    if (!value.trim()) {
      setSearchResults([]);
      return;
    }

    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ search: value }),
      });

      const data = await response.json();
      setSearchResults(data.results || []);
    } catch (error) {
      console.error("Search error:", error);
      setSearchResults([]);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Search
      </Typography>

      <TextField
        fullWidth
        label="Search"
        variant="outlined"
        value={searchTerm}
        onChange={(e) => handleSearch(e.target.value)}
        placeholder="Enter search term..."
        sx={{ mb: 3 }}
      />

      {searchResults.length > 0 && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Type</TableCell>
                <TableCell>Resource</TableCell>
                <TableCell>Module</TableCell>
                <TableCell>Details</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {searchResults.map((result, index) => (
                <TableRow key={index}>
                  <TableCell>{result.type}</TableCell>
                  <TableCell>{result.resource}</TableCell>
                  <TableCell>{result.module}</TableCell>
                  <TableCell>
                    {result.type === "observation" && result.attribute && (
                      <>
                        <strong>attribute:</strong> {result.attribute}
                        <br />
                        <strong>value:</strong> {result.value}
                        <br />
                        <strong>First seen:</strong> {result.first_seen}
                        <br />
                        <strong>Last seen:</strong> {result.last_seen}
                      </>
                    )}
                    {result.type === "change" && result.attribute && (
                      <>
                        <strong>attribute:</strong> {result.attribute}
                        <br />
                        <strong>old_value:</strong> {result.old_value}
                        <br />
                        <strong>new_value:</strong> {result.new_value}
                        <br />
                        <strong>First seen:</strong> {result.first_seen}
                        <br />
                        <strong>Last seen:</strong> {result.last_seen}
                      </>
                    )}
                    {result.type === "resource" && (
                      <>
                        <strong>Source:</strong> {result.source}
                        <br />
                        <strong>First seen:</strong> {result.first_seen}
                        <br />
                        <strong>Last seen:</strong> {result.last_seen}
                      </>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {searchTerm && searchResults.length === 0 && (
        <Paper sx={{ p: 2 }}>
          <Typography>No results found for "{searchTerm}"</Typography>
        </Paper>
      )}
    </Box>
  );
};

export default SearchView;
