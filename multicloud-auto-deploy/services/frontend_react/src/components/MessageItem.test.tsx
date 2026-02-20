import { vi } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render } from '../test/utils';
import PostItem from './MessageItem';
import type { Post } from '../types/message';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Mock the mutation hooks so tests never hit a real API
const mockUpdateMutateAsync = vi.fn().mockResolvedValue({});
const mockDeleteMutateAsync = vi.fn().mockResolvedValue({});

vi.mock('../hooks/useMessages', () => ({
  useUpdatePost: () => ({
    mutateAsync: mockUpdateMutateAsync,
    isPending: false,
  }),
  useDeletePost: () => ({
    mutateAsync: mockDeleteMutateAsync,
    isPending: false,
  }),
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const basePost: Post = {
  postId: 'post-001',
  userId: 'user-123',
  nickname: 'Alice',
  content: 'Hello, world!',
  isMarkdown: false,
  tags: ['react', 'test'],
  imageUrls: null,
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: null,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Test: display
// ---------------------------------------------------------------------------

describe('PostItem — display', () => {
  it('renders the post content', () => {
    render(<PostItem post={basePost} />);
    expect(screen.getByText('Hello, world!')).toBeInTheDocument();
  });

  it('shows nickname when provided', () => {
    render(<PostItem post={basePost} />);
    expect(screen.getByText('Alice')).toBeInTheDocument();
  });

  it('falls back to userId when nickname is absent', () => {
    render(<PostItem post={{ ...basePost, nickname: null }} />);
    expect(screen.getByText('user-123')).toBeInTheDocument();
  });

  it('renders tags as hashtag badges', () => {
    render(<PostItem post={basePost} />);
    expect(screen.getByText('#react')).toBeInTheDocument();
    expect(screen.getByText('#test')).toBeInTheDocument();
  });

  it('does not render tag section when tags list is empty', () => {
    render(<PostItem post={{ ...basePost, tags: [] }} />);
    expect(screen.queryByText(/#/)).not.toBeInTheDocument();
  });

  it('renders image thumbnails when imageUrls are present', () => {
    const post: Post = {
      ...basePost,
      imageUrls: ['/storage/simple-sns/img1.png', '/storage/simple-sns/img2.png'],
    };
    render(<PostItem post={post} />);
    const images = screen.getAllByRole('img', { name: '添付画像' });
    expect(images).toHaveLength(2);
    expect(images[0]).toHaveAttribute('src', '/storage/simple-sns/img1.png');
  });

  it('shows "編集済" label when updatedAt differs from createdAt', () => {
    const post: Post = {
      ...basePost,
      updatedAt: '2026-01-02T00:00:00Z',
    };
    render(<PostItem post={post} />);
    expect(screen.getByText(/編集済/)).toBeInTheDocument();
  });

  it('does not show "編集済" when updatedAt equals createdAt', () => {
    const post: Post = {
      ...basePost,
      updatedAt: basePost.createdAt,
    };
    render(<PostItem post={post} />);
    expect(screen.queryByText(/編集済/)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Test: editing mode
// ---------------------------------------------------------------------------

describe('PostItem — editing', () => {
  it('enters editing mode when ✏️ is clicked', async () => {
    const user = userEvent.setup();
    render(<PostItem post={basePost} />);
    await user.click(screen.getByTitle('編集'));
    expect(screen.getByDisplayValue('Hello, world!')).toBeInTheDocument();
  });

  it('cancels editing and restores original content', async () => {
    const user = userEvent.setup();
    render(<PostItem post={basePost} />);
    await user.click(screen.getByTitle('編集'));
    const contentBox = screen.getByDisplayValue('Hello, world!');
    await user.clear(contentBox);
    await user.type(contentBox, 'Changed');
    await user.click(screen.getByText('キャンセル'));
    expect(screen.getByText('Hello, world!')).toBeInTheDocument();
  });

  it('calls updatePost.mutateAsync on save', async () => {
    const user = userEvent.setup();
    render(<PostItem post={basePost} />);
    await user.click(screen.getByTitle('編集'));
    await user.click(screen.getByText(/保存/));
    await waitFor(() => {
      expect(mockUpdateMutateAsync).toHaveBeenCalledWith({
        postId: 'post-001',
        data: expect.objectContaining({ content: 'Hello, world!' }),
      });
    });
  });
});

// ---------------------------------------------------------------------------
// Test: deletion
// ---------------------------------------------------------------------------

describe('PostItem — deletion', () => {
  it('calls deletePost.mutateAsync after confirm', async () => {
    vi.spyOn(window, 'confirm').mockReturnValueOnce(true);
    const user = userEvent.setup();
    render(<PostItem post={basePost} />);
    await user.click(screen.getByTitle('削除'));
    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith('post-001');
    });
  });

  it('does NOT call deletePost.mutateAsync when confirm is cancelled', async () => {
    vi.spyOn(window, 'confirm').mockReturnValueOnce(false);
    const user = userEvent.setup();
    render(<PostItem post={basePost} />);
    await user.click(screen.getByTitle('削除'));
    expect(mockDeleteMutateAsync).not.toHaveBeenCalled();
  });
});
