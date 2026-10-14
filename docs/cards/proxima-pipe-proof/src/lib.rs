#[cfg(test)]
use core::convert::Infallible;
#[cfg(test)]
use core::future::Future;

#[cfg(test)]
use proxima_primitives::pipe::{Pipe, PipeExt};

#[cfg(test)]
struct NameLength;

#[cfg(test)]
impl Pipe for NameLength {
    type In = &'static str;
    type Out = usize;
    type Err = Infallible;

    fn call(&self, name: &'static str) -> impl Future<Output = Result<usize, Infallible>> {
        async move { Ok(name.len()) }
    }
}

#[cfg(test)]
struct IsNonEmpty;

#[cfg(test)]
impl Pipe for IsNonEmpty {
    type In = usize;
    type Out = bool;
    type Err = Infallible;

    fn call(&self, length: usize) -> impl Future<Output = Result<bool, Infallible>> {
        async move { Ok(length > 0) }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use core::task::{Context, Poll, Waker};

    fn block_on_ready<F: Future>(future: F) -> F::Output {
        let waker = Waker::noop();
        let mut context = Context::from_waker(waker);
        let mut future = core::pin::pin!(future);
        match future.as_mut().poll(&mut context) {
            Poll::Ready(output) => output,
            Poll::Pending => panic!("proof pipes are immediately ready"),
        }
    }

    #[test]
    fn composed_pipe_transforms_borrowed_input() {
        let pipe = NameLength.and_then(IsNonEmpty);
        assert_eq!(block_on_ready(pipe.call("demo")), Ok(true));
        assert_eq!(block_on_ready(pipe.call("")), Ok(false));
    }
}
