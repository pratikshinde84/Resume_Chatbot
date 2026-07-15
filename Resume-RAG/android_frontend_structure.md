# Android App Frontend Structure for Resume-RAG

This document describes the Android frontend architecture and the backend API endpoints needed to upload resumes, delete stored resumes, and ask questions using the uploaded resume data.

## 1. Backend API Endpoints

The Android app should call these endpoints from the Flask backend running in `Resume-RAG/upload_api.py`.

- `POST /upload`
  - Upload a resume PDF using multipart form data with field name `file`
  - Returns the saved resume filename and status

- `GET /resumes`
  - Returns a JSON list of all PDF files currently stored in `resumes/`
  - Example response: `{ "resumes": ["pratik.pdf", "amit.pdf"] }`

- `DELETE /resumes/{filename}`
  - Deletes the named resume file from `resumes/`
  - Example URL: `/resumes/pratik.pdf`

- `POST /query`
  - Sends a chat-style question to the resume search backend
  - Request JSON body: `{ "query": "Does any candidate have PyTorch experience?" }`
  - Response contains the answer and related source chunks

- `POST /rebuild`
  - Rebuilds the resume vector database after uploads or deletes
  - Useful for keeping the search index in sync with stored resumes

## 2. Android Project Architecture

Suggested package structure:

```
app/src/main/java/com/example/resumerag/
    MainActivity.kt
    data/
        ResumeItem.kt
        ChatMessage.kt
        ApiResult.kt
    network/
        ResumeApiService.kt
        NetworkClient.kt
    ui/
        ResumeScreen.kt
        ChatScreen.kt
        components/
            ResumeListItem.kt
            UploadButton.kt
            DeleteConfirmDialog.kt
            ChatMessageBubble.kt
            ChatInputBar.kt
    viewmodel/
        ResumeViewModel.kt
        ChatViewModel.kt
    util/
        FileUtils.kt
        UiState.kt
```

## 3. UI Flow

### Resume Management Screen

- `Upload Resume` button
  - Opens a file picker limited to PDF files
  - Sends selected file to `POST /upload`

- Resume list view
  - Shows stored PDF file names
  - Each row includes a `Delete` action
  - Tapping delete calls `DELETE /resumes/{filename}`
  - Refreshes the list after upload or deletion

- `Sync Index` button (optional)
  - Calls `POST /rebuild`
  - Ensures the RAG database is rebuilt before asking questions

### Chat Screen

- Chat area with a scrolling list of exchanged messages
- Input field for user query
- Send button calls `POST /query`
- Displays the AI answer and optionally the matched resume sources

## 4. Recommended Android Technologies

- Kotlin
- Jetpack Compose for modern UI
- Retrofit for HTTP API calls
- OkHttp for file uploads
- Kotlin Coroutines or Flow for asynchronous flows
- ViewModel + StateFlow for screen state management

## 5. Sample Retrofit API Interface

```kotlin
const val BASE_URL = "https://resume-chatbot-1-eutd.onrender.com"

interface ResumeApiService {
    @Multipart
    @POST("/upload")
    suspend fun uploadResume(@Part file: MultipartBody.Part): UploadResponse

    @GET("/resumes")
    suspend fun listResumes(): ResumeListResponse

    @DELETE("/resumes/{filename}")
    suspend fun deleteResume(@Path("filename") filename: String): DeleteResponse

    @POST("/query")
    suspend fun queryResume(@Body request: QueryRequest): QueryResponse

    @POST("/rebuild")
    suspend fun rebuildIndex(): RebuildResponse
}
```

## 6. Example UI Screens

- `ResumeScreen`
  - `TopAppBar(title = "Resume Manager")`
  - `Button(onClick = { viewModel.pickPdfFile() }) { Text("Upload Resume") }`
  - `LazyColumn` for stored resumes
  - `OutlinedButton(onClick = { viewModel.deleteResume(resume.name) }) { Text("Delete") }`

- `ChatScreen`
  - `TopAppBar(title = "Resume Chat")`
  - `LazyColumn` for chat messages
  - `TextField(value = prompt, onValueChange = { ... })`
  - `Button(onClick = { viewModel.sendQuery(prompt) }) { Text("Send") }`

## 7. Startup and Next Steps

1. Use the deployed backend at `https://resume-chatbot-1-eutd.onrender.com` or run the Flask/FastAPI backend locally on `http://<host>:8000`
2. Create the Android app skeleton in Android Studio
3. Implement the Retrofit client using the API endpoints above
4. Add file upload and deletion logic in `ResumeViewModel`
5. Add chat input, display, and query handling in `ChatViewModel`

---

This structure gives you native Android frontend flow plus the required backend API support for upload, delete, and resume-based chat queries.
