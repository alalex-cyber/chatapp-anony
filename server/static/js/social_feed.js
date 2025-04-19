// social_feed.js - Handles posts, comments, and reactions

// Socket.IO connection
const socket = io();

// DOM elements
const postForm = document.getElementById('post-form');
const postInput = document.getElementById('post-input');
const fileInput = document.getElementById('file-input');
const feedContainer = document.getElementById('feed-container');

// Load posts when the page is ready
document.addEventListener('DOMContentLoaded', () => {
    loadPosts();

    // Connect to socket for real-time updates
    socket.on('connect', () => {
        console.log('Connected to social feed');
    });
});

// Load posts from API
function loadPosts(page = 1) {
    fetch(`/api/posts?page=${page}&per_page=10`)
        .then(response => response.json())
        .then(data => {
            displayPosts(data.posts);
            setupPagination(data.pagination);
        })
        .catch(error => console.error('Error loading posts:', error));
}

// Display posts in the container
function displayPosts(posts) {
    if (posts.length === 0) {
        feedContainer.innerHTML = '<div class="no-posts">No posts yet. Be the first to share something!</div>';
        return;
    }

    // Clear container if it's the first page
    if (!feedContainer.dataset.appending) {
        feedContainer.innerHTML = '';
    }

    posts.forEach(post => {
        const postElement = createPostElement(post);
        feedContainer.appendChild(postElement);
    });
}

// Create a post element
function createPostElement(post) {
    const div = document.createElement('div');
    div.className = 'post-card';
    div.setAttribute('data-post-id', post.id);

    // Format the post date
    const postDate = formatDate(post.created_at);

    // Create the HTML structure for the post
    div.innerHTML = `
        <div class="post-header">
            <div class="post-user">
                <div class="post-avatar ${post.author.avatar_color}">
                    <div class="avatar-face ${post.author.avatar_face}">
                        <div class="avatar-dot left"></div>
                        <div class="avatar-dot right"></div>
                        <div class="avatar-mouth"></div>
                    </div>
                </div>
                <div class="post-user-info">
                    <div class="post-username">${post.author.alias}</div>
                    <div class="post-time">${postDate}</div>
                </div>
            </div>
            <div class="post-more">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="1"></circle>
                    <circle cx="19" cy="12" r="1"></circle>
                    <circle cx="5" cy="12" r="1"></circle>
                </svg>
            </div>
        </div>
        <div class="post-content">
            <p class="post-text">${post.content}</p>
            ${post.image_url ? `<img src="${post.image_url}" alt="Posted image" class="post-image">` : ''}
        </div>
        <div class="post-stats">
            <div class="post-likes">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="${post.user_liked ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
                </svg>
                <span class="like-count">${post.like_count}</span> likes
            </div>
            <div class="post-comments-count">
                <span class="comment-count">${post.comment_count}</span> comments
            </div>
        </div>
        <div class="post-actions">
            <button class="post-action ${post.user_liked ? 'liked' : ''}" data-action="like">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="${post.user_liked ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
                </svg>
                Like
            </button>
            <button class="post-action" data-action="comment">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                Comment
            </button>
            <button class="post-action" data-action="share">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path>
                    <polyline points="16 6 12 2 8 6"></polyline>
                    <line x1="12" y1="2" x2="12" y2="15"></line>
                </svg>
                Share
            </button>
        </div>
        <div class="comments-section" id="comments-${post.id}" style="display: none;">
            <div class="comment-input-container">
                <div class="comment-avatar"></div>
                <div class="comment-input-wrapper">
                    <input type="text" class="comment-input" placeholder="Write a comment..." data-post-id="${post.id}">
                    <button class="comment-submit" data-post-id="${post.id}">Post</button>
                </div>
            </div>
            <div class="comments-list" id="comments-list-${post.id}">
                <!-- Comments will be loaded here -->
            </div>
            <div class="view-more-comments" data-post-id="${post.id}">
                View more comments
            </div>
        </div>
    `;

    // Add event listeners to the post element
    setupPostEventListeners(div, post);

    return div;
}

// Setup event listeners for a post element
function setupPostEventListeners(postElement, post) {
    // Like button
    const likeButton = postElement.querySelector('.post-action[data-action="like"]');
    likeButton.addEventListener('click', () => {
        toggleLike(post.id, likeButton);
    });

    // Comment button
    const commentButton = postElement.querySelector('.post-action[data-action="comment"]');
    commentButton.addEventListener('click', () => {
        toggleComments(post.id);
    });

    // Comment submit button
    const commentSubmit = postElement.querySelector('.comment-submit');
    commentSubmit.addEventListener('click', () => {
        const commentInput = postElement.querySelector('.comment-input');
        submitComment(post.id, commentInput.value);
        commentInput.value = '';
    });

    // Comment input (enter key)
    const commentInput = postElement.querySelector('.comment-input');
    commentInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            submitComment(post.id, commentInput.value);
            commentInput.value = '';
        }
    });

    // View more comments
    const viewMoreComments = postElement.querySelector('.view-more-comments');
    viewMoreComments.addEventListener('click', () => {
        loadComments(post.id);
    });
}

// Toggle like on a post
function toggleLike(postId, likeButton) {
    // Send request to like/unlike the post
    fetch('/api/reactions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            target_id: postId,
            target_type: 'post',
            reaction_type: 'like'
        })
    })
    .then(response => response.json())
    .then(data => {
        // Update UI based on response
        const likeIcon = likeButton.querySelector('svg');
        const likeCount = likeButton.closest('.post-card').querySelector('.like-count');

        if (data.status === 'added') {
            likeButton.classList.add('liked');
            likeIcon.setAttribute('fill', 'currentColor');
            likeCount.textContent = parseInt(likeCount.textContent) + 1;
        } else {
            likeButton.classList.remove('liked');
            likeIcon.setAttribute('fill', 'none');
            likeCount.textContent = parseInt(likeCount.textContent) - 1;
        }
    })
    .catch(error => console.error('Error toggling like:', error));
}

// Show/hide comments section
function toggleComments(postId) {
    const commentsSection = document.getElementById(`comments-${postId}`);

    if (commentsSection.style.display === 'none') {
        commentsSection.style.display = 'block';
        loadComments(postId);
    } else {
        commentsSection.style.display = 'none';
    }
}

// Load comments for a post
function loadComments(postId) {
    fetch(`/api/posts/${postId}/comments`)
        .then(response => response.json())
        .then(comments => {
            displayComments(postId, comments);
        })
        .catch(error => console.error('Error loading comments:', error));
}

// Display comments for a post
function displayComments(postId, comments) {
    const commentsContainer = document.getElementById(`comments-list-${postId}`);

    if (comments.length === 0) {
        commentsContainer.innerHTML = '<div class="no-comments">No comments yet. Be the first to comment!</div>';
        return;
    }

    commentsContainer.innerHTML = '';

    comments.forEach(comment => {
        const commentElement = createCommentElement(comment);
        commentsContainer.appendChild(commentElement);
    });
}

// Create a comment element
function createCommentElement(comment) {
    const div = document.createElement('div');
    div.className = 'comment';
    div.setAttribute('data-comment-id', comment.id);

    div.innerHTML = `
        <div class="comment-avatar ${comment.author.avatar_color}">
            <div class="avatar-face ${comment.author.avatar_face}">
                <div class="avatar-dot left"></div>
                <div class="avatar-dot right"></div>
                <div class="avatar-mouth"></div>
            </div>
        </div>
        <div class="comment-content">
            <div class="comment-username">${comment.author.alias}</div>
            <div class="comment-text">${comment.content}</div>
            <div class="comment-actions">
                <span class="comment-action like-comment ${comment.user_liked ? 'liked' : ''}" data-action="like" data-comment-id="${comment.id}">Like</span>
                <span class="comment-action" data-action="reply" data-comment-id="${comment.id}">Reply</span>
                <span class="comment-time">${formatTime(comment.created_at)}</span>
            </div>
        </div>
    `;

    // Add event listeners to comment actions
    const likeAction = div.querySelector('.comment-action[data-action="like"]');
    likeAction.addEventListener('click', () => {
        toggleCommentLike(comment.id, likeAction);
    });

    return div;
}

// Toggle like on a comment
function toggleCommentLike(commentId, likeElement) {
    fetch('/api/reactions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            target_id: commentId,
            target_type: 'comment',
            reaction_type: 'like'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'added') {
            likeElement.classList.add('liked');
        } else {
            likeElement.classList.remove('liked');
        }
    })
    .catch(error => console.error('Error toggling comment like:', error));
}

// Submit a new comment
function submitComment(postId, content) {
    if (!content.trim()) return;

    fetch(`/api/posts/${postId}/comments`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            content: content
        })
    })
    .then(response => response.json())
    .then(comment => {
        // Add the new comment to the list
        const commentsContainer = document.getElementById(`comments-list-${postId}`);
        const commentElement = createCommentElement(comment);
        commentsContainer.appendChild(commentElement);

        // Update comment count
        const commentCount = document.querySelector(`.post-card[data-post-id="${postId}"] .comment-count`);
        commentCount.textContent = parseInt(commentCount.textContent) + 1;
    })
    .catch(error => console.error('Error posting comment:', error));
}

// Create a new post
function createPost(content, file) {
    const formData = new FormData();
    formData.append('content', content);

    if (file) {
        formData.append('image', file);
    }

    fetch('/api/posts', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(post => {
        // Add the new post to the feed
        const postElement = createPostElement(post);
        feedContainer.insertBefore(postElement, feedContainer.firstChild);

        // Clear the form
        postInput.value = '';
        if (fileInput) fileInput.value = '';
    })
    .catch(error => console.error('Error creating post:', error));
}

// Handle post form submission
if (postForm) {
    postForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const content = postInput.value;
        const file = fileInput ? fileInput.files[0] : null;
        createPost(content, file);
    });
}

// Format date for posts
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
        return `Today at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } else if (diffDays === 1) {
        return 'Yesterday';
    } else if (diffDays < 7) {
        return date.toLocaleDateString([], { weekday: 'long' });
    } else {
        return date.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
    }
}

// Format time for comments
function formatTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffMinutes = Math.floor(diffTime / (1000 * 60));

    if (diffMinutes < 1) {
        return 'Just now';
    } else if (diffMinutes < 60) {
        return `${diffMinutes}m`;
    } else if (diffMinutes < 1440) {
        return `${Math.floor(diffMinutes / 60)}h`;
    } else {
        return `${Math.floor(diffMinutes / 1440)}d`;
    }
}

// Setup pagination
function setupPagination(paginationData) {
    const paginationElement = document.getElementById('pagination');
    if (!paginationElement) return;

    paginationElement.innerHTML = '';

    if (paginationData.pages > 1) {
        // Previous button
        if (paginationData.has_prev) {
            const prevButton = document.createElement('button');
            prevButton.className = 'pagination-button';
            prevButton.textContent = 'Previous';
            prevButton.addEventListener('click', () => {
                feedContainer.dataset.appending = false;
                loadPosts(paginationData.page - 1);
            });
            paginationElement.appendChild(prevButton);
        }

        // Page indicator
        const pageIndicator = document.createElement('span');
        pageIndicator.className = 'page-indicator';
        pageIndicator.textContent = `Page ${paginationData.page} of ${paginationData.pages}`;
        paginationElement.appendChild(pageIndicator);

        // Next button
        if (paginationData.has_next) {
            const nextButton = document.createElement('button');
            nextButton.className = 'pagination-button';
            nextButton.textContent = 'Next';
            nextButton.addEventListener('click', () => {
                feedContainer.dataset.appending = false;
                loadPosts(paginationData.page + 1);
            });
            paginationElement.appendChild(nextButton);
        }
    }
}

// Listen for new posts via Socket.IO
socket.on('new_post', (post) => {
    // Add the new post to the feed if it's not already there
    if (!document.querySelector(`.post-card[data-post-id="${post.id}"]`)) {
        const postElement = createPostElement(post);
        feedContainer.insertBefore(postElement, feedContainer.firstChild);
    }
});

// Listen for new comments via Socket.IO
socket.on('new_comment', (comment) => {
    // Add the new comment if comments section is open
    const commentsSection = document.getElementById(`comments-${comment.post_id}`);
    if (commentsSection && commentsSection.style.display !== 'none') {
        const commentsContainer = document.getElementById(`comments-list-${comment.post_id}`);
        const commentElement = createCommentElement(comment);
        commentsContainer.appendChild(commentElement);

        // Update comment count
        const commentCount = document.querySelector(`.post-card[data-post-id="${comment.post_id}"] .comment-count`);
        commentCount.textContent = parseInt(commentCount.textContent) + 1;
    }
});