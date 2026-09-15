"""초파리 연결체 모양 희소 행렬곱과 기울기. 딥러닝 체스 신경망의 핵심 연산.

y = W x,  W[post, pre] = vals  (연결 목록 모양 그대로, 부호는 vals 쪽에서 고정)
PyTorch 기본 희소 autograd는 COO 역전파에서 N x N 밀집 기울기(127,400² = 60 GiB)를 만들어서 못 쓴다.
그래서 기울기를 직접 계산한다: grad_x = W^T grad_y (CSR), grad_vals = sum_batch grad_y[post] * x[pre] (배치를 나눠서).
"""
import torch


class Conn:
    """연결 목록(pre, post)을 CSR 순서로 한 번만 정렬해 두는 그릇."""

    def __init__(self, pre, post, n, device):
        self.n = n
        pre = torch.as_tensor(pre, dtype=torch.long, device=device)
        post = torch.as_tensor(post, dtype=torch.long, device=device)
        self.pre, self.post = pre, post
        self.fwd = self._csr(post, pre)   # 행 = 받는 뉴런
        self.bwd = self._csr(pre, post)   # 행 = 보내는 뉴런 (전치)

    def _csr(self, rows, cols):
        order = torch.argsort(rows * self.n + cols)
        crow = torch.zeros(self.n + 1, dtype=torch.long, device=rows.device)
        crow[1:] = torch.bincount(rows, minlength=self.n).cumsum(0)
        return order, crow, cols[order]

    def matrix(self, vals, transpose=False):
        order, crow, col = self.bwd if transpose else self.fwd
        return torch.sparse_csr_tensor(crow, col, vals[order], size=(self.n, self.n))


class ConnMatMul(torch.autograd.Function):
    @staticmethod
    def forward(ctx, vals, x, conn, chunk):
        ctx.save_for_backward(vals, x)
        ctx.conn, ctx.chunk = conn, chunk
        return (conn.matrix(vals) @ x.t()).t()

    @staticmethod
    def backward(ctx, gy):
        vals, x = ctx.saved_tensors
        conn, chunk = ctx.conn, ctx.chunk
        gx = (conn.matrix(vals, transpose=True) @ gy.t()).t()
        gv = torch.zeros_like(vals)
        for i in range(0, x.shape[0], chunk):
            gv += (gy[i:i + chunk, conn.post] * x[i:i + chunk, conn.pre]).sum(0)
        return gv, gx, None, None


def conn_matmul(vals, x, conn, chunk=8):
    """vals: [edges], x: [batch, neurons] → [batch, neurons]"""
    return ConnMatMul.apply(vals, x, conn, chunk)


def self_test(device='cpu'):
    """작은 무작위 그래프에서 기울기가 밀집 행렬 autograd와 같은지 확인."""
    g = torch.Generator().manual_seed(0)
    n = 60
    keys = torch.unique(torch.randint(0, n * n, (400,), generator=g))
    post, pre = (keys // n).to(device), (keys % n).to(device)
    conn = Conn(pre, post, n, device)
    v1 = torch.randn(len(keys), generator=g).to(device).requires_grad_()
    x1 = torch.randn(5, n, generator=g).to(device).requires_grad_()
    dense = torch.zeros(n, n, device=device).index_put((post, pre), v1)
    ((dense @ x1.t()).t().pow(2).sum()).backward()
    v2 = v1.detach().clone().requires_grad_()
    x2 = x1.detach().clone().requires_grad_()
    conn_matmul(v2, x2, conn, chunk=2).pow(2).sum().backward()
    ok = torch.allclose(v1.grad, v2.grad, atol=1e-4) and torch.allclose(x1.grad, x2.grad, atol=1e-4)
    assert ok, 'conn_matmul gradient mismatch'
    return ok


if __name__ == '__main__':
    print('gradient matches dense autograd:', self_test('cpu'))
