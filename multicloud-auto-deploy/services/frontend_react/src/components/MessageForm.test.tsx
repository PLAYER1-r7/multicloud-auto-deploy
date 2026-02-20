import { vi } from 'vitest';
import { screen, waitFor, fireEvent } from '../test/utils';
import userEvent from '@testing-library/user-event';
import { render } from '../test/utils';
import PostForm from './MessageForm';

// ---------------------------------------------------------------------------
// Mock
// ---------------------------------------------------------------------------

const mockMutateAsync = vi.fn().mockResolvedValue({});

vi.mock('../hooks/useMessages', () => ({
  useCreatePost: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
    isError: false,
  }),
}));

beforeEach(() => vi.clearAllMocks());

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('PostForm', () => {
  it('renders the form fields', () => {
    render(<PostForm />);
    expect(screen.getByPlaceholderText('今何を考えていますか？')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('react, typescript, cloud')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /投稿する/ })).toBeInTheDocument();
  });

  it('submit button is disabled when content is empty', () => {
    render(<PostForm />);
    expect(screen.getByRole('button', { name: /投稿する/ })).toBeDisabled();
  });

  it('enables submit button when content is typed', async () => {
    const user = userEvent.setup();
    render(<PostForm />);
    await user.type(screen.getByPlaceholderText('今何を考えていますか？'), 'Hello');
    expect(screen.getByRole('button', { name: /投稿する/ })).toBeEnabled();
  });

  it('calls createPost.mutateAsync with content and tags on submit', async () => {
    const user = userEvent.setup();
    render(<PostForm />);
    await user.type(screen.getByPlaceholderText('今何を考えていますか？'), 'My post');
    await user.type(screen.getByPlaceholderText('react, typescript, cloud'), 'ts, vite');
    await user.click(screen.getByRole('button', { name: /投稿する/ }));
    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        content: 'My post',
        tags: ['ts', 'vite'],
        is_markdown: false,
      });
    });
  });

  it('clears the fields after successful submission', async () => {
    const user = userEvent.setup();
    render(<PostForm />);
    const textarea = screen.getByPlaceholderText('今何を考えていますか？');
    await user.type(textarea, 'Temporary');
    await user.click(screen.getByRole('button', { name: /投稿する/ }));
    await waitFor(() => {
      expect(textarea).toHaveValue('');
    });
  });

  it('does not call mutateAsync when content is blank', async () => {
    const user = userEvent.setup();
    render(<PostForm />);
    // The button is disabled, but also test direct form submit
    const form = screen.getByRole('button', { name: /投稿する/ }).closest('form')!;
    fireEvent.submit(form);
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });
});
