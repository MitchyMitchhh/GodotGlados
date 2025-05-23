import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './app.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import { Container, Row, Col, Card, Form, Button, Spinner, Badge, Alert } from 'react-bootstrap';

interface CollectionResult {
  source: string;
  text: string;
  score: number;
}

interface Context {
  collection: string;
  results: CollectionResult[];
}

interface QueryResponse {
  query: string;
  project_rules?: string;
  contexts: Context[];
}

interface LoadingState {
  indexProject: boolean;
  indexDocs: boolean;
  query: boolean;
  collections: boolean;
}

interface AlertState {
  show: boolean;
  variant: string;
  message: string;
}

// API base URL - change this based on your deployment
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

function App() {
  // State variables
  const [collections, setCollections] = useState<string[]>([]);
  const [selectedCollections, setSelectedCollections] = useState<string[]>([]);
  const [projectPath, setProjectPath] = useState<string>('');
  const [rulesFile, setRulesFile] = useState<File | null>(null);
  const [queryText, setQueryText] = useState<string>('');
  const [includeRules, setIncludeRules] = useState<boolean>(true);
  const [queryResults, setQueryResults] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState<LoadingState>({
    indexProject: false,
    indexDocs: false,
    query: false,
    collections: false
  });
  const [alert, setAlert] = useState<AlertState>({ show: false, variant: 'info', message: '' });

  const showAlert = (message: string, variant: string = 'info') => {
    setAlert({ show: true, variant, message });
    // Auto hide after 10 seconds
    setTimeout(() => setAlert({ show: false, variant: 'info', message: '' }), 10000);
  };

  useEffect(() => {
    const checkApiStatus = async () => {
      try {
        await axios.get(`${API_URL.replace('/api', '')}/health`);
      } catch (error) {
        showAlert(`API may be starting up or unavailable. Connecting to: ${API_URL}`, 'warning');
        console.log('API status check failed:', error);
      }
    };
    
    checkApiStatus();
  }, []);

  useEffect(() => {
    fetchCollections();
  }, []);

  const fetchCollections = async () => {
    setLoading(prev => ({ ...prev, collections: true }));
    
    try {
      const response = await axios.get(`${API_URL}/collections`);
      if (response.data.success && response.data.collections.length > 0) {
        setCollections(response.data.collections);
        setSelectedCollections(response.data.collections);
      }
    } catch (error) {
      console.error('Error fetching collections:', error);
      // Don't show error, as the backend might be cold-starting
    } finally {
      setLoading(prev => ({ ...prev, collections: false }));
    }
  };

  const handleIndexProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectPath) {
      showAlert('Please enter a project path', 'danger');
      return;
    }

    setLoading(prev => ({ ...prev, indexProject: true }));
    
    try {
      if (rulesFile) {
        const formData = new FormData();
        formData.append('file', rulesFile);
        
        await axios.post(`${API_URL}/upload-rules`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
      }
      
      const response = await axios.post(`${API_URL}/index-project`, {
        project_path: projectPath,
        chunk_size: 1000,
        chunk_overlap: 200
      });
      
      if (response.data.success) {
        showAlert('Project indexed successfully!', 'success');
        fetchCollections();
      }
    } catch (error: any) {
      console.error('Error indexing project:', error);
      showAlert(`Error indexing project: ${error.response?.data?.detail || error.message}`, 'danger');
    } finally {
      setLoading(prev => ({ ...prev, indexProject: false }));
    }
  };

  const handleIndexDocs = async () => {
    setLoading(prev => ({ ...prev, indexDocs: true }));
    
    try {
      const response = await axios.post(`${API_URL}/index-docs`, {
        version: 'stable',
        collection: 'godot_docs'
      });
      
      if (response.data.success) {
        showAlert('Godot documentation indexed successfully!', 'success');
        fetchCollections();
      }
    } catch (error: any) {
      console.error('Error indexing docs:', error);
      showAlert(`Error indexing documentation: ${error.response?.data?.detail || error.message}`, 'danger');
    } finally {
      setLoading(prev => ({ ...prev, indexDocs: false }));
    }
  };

  const copyResultsToClipboard = (data: QueryResponse) => {
    if (!data || !data.contexts || data.contexts.length === 0) {
      return false;
    }
    
    try {
      let clipboardText = `Prompt: ${data.query}\n\n`;
      if (data.project_rules != null) {
        clipboardText += data.project_rules;
      }
      data.contexts.forEach(context => {
        clipboardText += `From ${context.collection}:\n`;
        
        context.results.forEach(result => {
          clipboardText += `Source: ${result.source}\n${result.text}\n\n`;
        });
      });
      
      navigator.clipboard.writeText(clipboardText)
        .then(() => {
          console.log('Successfully copied to clipboard');
          return true;
        })
        .catch(err => {
          console.error('Failed to copy to clipboard:', err);
          return false;
        });
        
      return true;
    } catch (error) {
      console.error('Error in clipboard function:', error);
      return false;
    }
  };

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryText.trim()) {
      showAlert('Please enter a query', 'warning');
      return;
    }
    
    setLoading(prev => ({ ...prev, query: true }));
    
    try {
      const response = await axios.post(`${API_URL}/query`, {
        query: queryText,
        collections: selectedCollections,
        include_rules: includeRules
      });
      // Set results for UI display
      setQueryResults(response.data);
      
      if (response.data.contexts.length === 0) {
        showAlert('No relevant results found. Try a different query.', 'info');
      } else {
        try {
          const copied = copyResultsToClipboard({...response.data});
          
          if (copied) {
            showAlert('Context copied to clipboard!', 'success');
          } else {
            showAlert('Context retrieved successfully!', 'success');
          }
        } catch (clipError) {
          console.error('Error in clipboard function call:', clipError);
          showAlert('Context retrieved successfully!', 'success');
        }
      }
    } catch (error: any) {
      console.error('Error querying:', error);
      showAlert(`Error querying: ${error.response?.data?.detail || error.message}`, 'danger');
    } finally {
      setLoading(prev => ({ ...prev, query: false }));
    }
  };

  const handleCollectionChange = (collection: string) => {
    if (selectedCollections.includes(collection)) {
      setSelectedCollections(selectedCollections.filter(c => c !== collection));
    } else {
      setSelectedCollections([...selectedCollections, collection]);
    }
  };

  const formatContent = (text: string) => {
    const isCode = text.includes('func ') || 
                   text.includes('var ') || 
                   text.includes('import ') ||
                   text.includes('class ');
    
    if (isCode) {
      return <pre className="mb-0 bg-light p-3 rounded">{text}</pre>;
    } else {
      const formattedText = text
        .replace(/# (.*)/g, '<h5>$1</h5>')
        .replace(/## (.*)/g, '<h6>$1</h6>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n- (.*)/g, '<br>• $1')
        .replace(/\n/g, '<br>');
      
      return <div dangerouslySetInnerHTML={{ __html: formattedText }} />;
    }
  };

  return (
    <div className="App bg-light min-vh-100">
      <header className="bg-dark text-white py-3 mb-4">
        <Container className="d-flex align-items-center justify-content-center">
          <img 
            src="https://godotengine.org/assets/logo.svg" 
            alt="Godot Logo" 
            height="40" 
            className="me-3"
          />
          <h1 className="m-0">Glados</h1>
        </Container>
      </header>
      
      <Container fluid>
        {alert.show && (
          <Alert 
            variant={alert.variant} 
            dismissible 
            onClose={() => setAlert({ show: false, variant: 'info', message: '' })}
            className="mb-3"
          >
            {alert.message}
          </Alert>
        )}
        
        <Row>
          <Col md={5}>
            <Card className="shadow-sm mb-4">
              <Card.Header className="bg-primary text-white">
                <h5 className="mb-0">Project Configuration</h5>
              </Card.Header>
              <Card.Body>
                <Form onSubmit={handleIndexProject}>
                  <Form.Group className="mb-3">
                    <Form.Label>Godot Project Path</Form.Label>
                    <Form.Control
                      type="text"
                      placeholder="C:\Users\Username\GodotProjects\MyGame"
                      value={projectPath}
                      onChange={(e) => setProjectPath(e.target.value)}
                    />
                  </Form.Group>
                  
                  <Form.Group className="mb-3">
                    <Form.Label>Rules File (Optional)</Form.Label>
                    <Form.Control
                      type="file"
                      accept=".md,.txt"
                      onChange={(e) => {
                        const files = (e.target as HTMLInputElement).files;
                        if (files && files.length > 0) {
                          setRulesFile(files[0]);
                        }
                      }}
                    />
                    <Form.Text className="text-muted">
                      Upload your project_rules.md file
                    </Form.Text>
                  </Form.Group>

                  <Button 
                    variant="primary" 
                    type="submit"
                    disabled={loading.indexProject || !projectPath}
                  >
                    {loading.indexProject ? (
                      <>
                        <Spinner
                          as="span"
                          animation="border"
                          size="sm"
                          role="status"
                          aria-hidden="true"
                          className="me-2"
                        />
                        Indexing...
                      </>
                    ) : (
                      'Index Project'
                    )}
                  </Button>
                </Form>
              </Card.Body>
            </Card>

            <Card className="shadow-sm mb-4">
              <Card.Header className="bg-success text-white">
                <h5 className="mb-0">Godot Documentation</h5>
              </Card.Header>
              <Card.Body>
                <div>
                  Only index the godot docs if a new version comes out. It can take several minutes to index.
                </div>
                <Button 
                  variant="success" 
                  onClick={handleIndexDocs}
                  disabled={loading.indexDocs}
                  className="mt-2"
                >
                  {loading.indexDocs ? (
                    <>
                      <Spinner
                        as="span"
                        animation="border"
                        size="sm"
                        role="status"
                        aria-hidden="true"
                        className="me-2"
                      />
                      Indexing Docs...
                    </>
                  ) : (
                    'Index Godot Docs'
                  )}
                </Button>
              </Card.Body>
            </Card>
          </Col>

          <Col md={7}>
            <Card className="shadow-sm mb-4">
              <Card.Header className="bg-info text-white">
                <h5 className="mb-0">Ask Glados for help :)</h5>
              </Card.Header>
              <Card.Body>
                <Form onSubmit={handleQuery}>
                  <Form.Group className="mb-3">
                    <Form.Label>What would you like to know?</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={6}
                      placeholder="E.g., How do I implement player movement?"
                      value={queryText}
                      onChange={(e) => setQueryText(e.target.value)}
                    />
                  </Form.Group>
                  <div className="mb-4"></div>
                  <Form.Group className="mb-3">
                    <Form.Check
                      type="checkbox"
                      id="include-rules"
                      label="Include Project Rules"
                      checked={includeRules}
                      onChange={(e) => setIncludeRules(e.target.checked)}
                    />
                  </Form.Group>

                  <Card className="shadow-sm mb-4">
                    <Card.Header className="bg-info text-white">
                      <h6 className="mb-0">Included Collections</h6>
                    </Card.Header>
                  <Card.Body>
                    {loading.collections ? (
                      <div className="text-center py-3">
                        <Spinner animation="border" size="sm" role="status" />
                        <span className="ms-2">Loading collections...</span>
                      </div>
                  ) : collections.length > 0 ? (
                    <>
                    {collections.map(collection => (
                      <Form.Check
                        key={collection}
                        type="checkbox"
                        id={`collection-${collection}`}
                        label={collection}
                        checked={selectedCollections.includes(collection)}
                        onChange={() => handleCollectionChange(collection)}
                        className="mb-2"
                      />
                    ))}
                    </>
                  ) : (
                    <p className="text-muted">No collections found. Index a project or docs first.</p>
                  )}
                    </Card.Body>
                  </Card>

                  <Button 
                    variant="info" 
                    type="submit"
                    className="text-white"
                    disabled={loading.query || !queryText.trim() || selectedCollections.length === 0}
                  >
                    {loading.query ? (
                      <>
                        <Spinner
                          as="span"
                          animation="border"
                          size="sm"
                          role="status"
                          aria-hidden="true"
                          className="me-2"
                        />
                        Querying...
                      </>
                    ) : (
                      'Submit Query'
                    )}
                  </Button>
                </Form>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {queryResults && (
          <Row>
            <Col xs={12}>
              <div className="mt-4">
                <h5>Results for: "{queryResults.query}"</h5>
                
                {/* Display project rules if available */}
                {queryResults.project_rules && (
                  <Card className="mb-4 shadow-sm">
                    <Card.Header className="bg-warning">
                      <h6 className="mb-0">Project Rules</h6>
                    </Card.Header>
                    <Card.Body>
                      {formatContent(queryResults.project_rules)}
                    </Card.Body>
                  </Card>
                )}
                
                {queryResults.contexts.length > 0 ? (
                  queryResults.contexts.map((context, contextIndex) => (
                    <div key={contextIndex} className="mb-4">
                      <h6 className="mt-3 mb-2">From {context.collection}:</h6>
                      
                      {context.results.map((result, resultIndex) => (
                        <Card key={`${contextIndex}-${resultIndex}`} className="mb-3 border-left-primary shadow-sm">
                          <Card.Body>
                            <Badge 
                              bg="info" 
                              className="position-absolute top-0 end-0 mt-2 me-2"
                            >
                              Score: {(result.score * 100).toFixed(1)}%
                            </Badge>
                            
                            <Card.Subtitle className="mb-2 text-muted">
                              Source: {result.source}
                            </Card.Subtitle>
                            
                            <div className="mt-3">
                              {formatContent(result.text)}
                            </div>
                          </Card.Body>
                        </Card>
                      ))}
                    </div>
                  ))
                ) : (
                  <div className="text-center py-4 my-3 bg-white rounded shadow-sm">
                    <p className="text-muted">No results found. Try a different query or index more content.</p>
                  </div>
                )}
              </div>
            </Col>
          </Row>
        )}

        <footer className="text-center py-4 mt-5 text-muted">
          <small>Godot RAG Service</small>
        </footer>
      </Container>
    </div>
  );
}

export default App;
